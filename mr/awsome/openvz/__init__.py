from lazy import lazy
from mr.awsome.common import BaseMaster, StartupScriptMixin
from mr.awsome.config import BooleanMassager, IntegerMassager, PathMassager
from mr.awsome.config import StartupScriptMassager, UserMassager
from mr.awsome.plain import Instance as PlainInstance
import logging
import sys
import time


log = logging.getLogger('mr.awsome.openvz')


class OpenVZError(Exception):
    pass


class Instance(PlainInstance, StartupScriptMixin):
    sectiongroupname = 'vz-instance'

    def get_host(self):
        return self.config['ip']

    def get_fingerprint(self):
        out, err = self.master.vzctl('exec', self.config['veid'], cmd='ssh-keygen -lf /etc/ssh/ssh_host_rsa_key.pub')
        info = out.split()
        return info[1]

    def vzlist(self, **kwargs):
        try:
            return self.master.vzlist(**kwargs)
        except ValueError as e:
            if e.args[0] == "VE not found":
                log.info("Instance unavailable")
                return
            log.error(e.args[0])
            sys.exit(1)

    def status(self):
        status = self.vzlist(veid=self.config['veid'])
        if status['status'] != 'running':
            log.info("Instance state: %s", status['status'])
            return
        log.info("Instance running.")
        log.info("Instances host name %s", status['hostname'])
        log.info("Instances ip address %s", status['ip'])

    def start(self, overrides=None):
        status = self.vzlist(veid=self.config['veid'])
        create = False
        if status is None:
            create = True
            log.info("Creating instance '%s'", self.config['veid'])
            try:
                self.master.vzctl(
                    'create',
                    self.config['veid'],
                    ip=self.config['ip'],
                    hostname=self.config['hostname'],
                    ostemplate=self.config['ostemplate'])
            except OpenVZError as e:
                for line in e.args[0].split('\n'):
                    log.error(line)
                sys.exit(1)
        else:
            if status['status'] != 'stopped':
                log.info("Instance state: %s", status['status'])
                log.info("Instance already started")
                return True
        options = {}
        for key in self.config:
            if key.startswith('set-'):
                options[key] = self.config[key]
        if options:
            self.master.vzctl('set', self.config['veid'], save=True, **options)
        log.info("Starting instance '%s'", self.config['veid'])
        self.master.vzctl('start', self.config['veid'])
        startup_script = self.startup_script(overrides=overrides)
        if create and startup_script:
            log.info("Instance started, waiting until it's available")
            for i in range(60):
                sys.stdout.write(".")
                sys.stdout.flush()
                out, err = self.master.vzctl('exec', self.config['veid'], cmd="runlevel")
                if not out.startswith("unknown"):
                    break
                time.sleep(5)
            else:
                log.error("Timeout while waiting for instance to start after creation!")
                sys.exit(1)
            sys.stdout.write("\n")
            sys.stdout.flush()
            log.info("Running startup_script")
            cmd_fmt = 'base64 -d > /etc/startup_script <<_END_OF_SCRIPT_\n%s\n_END_OF_SCRIPT_\n'
            cmd = cmd_fmt % startup_script.encode('base64')
            out, err = self.master.vzctl(
                'exec',
                self.config['veid'],
                cmd=cmd)
            if out:
                for line in out.split('\n'):
                    log.info(line)
            if err:
                for line in err.split('\n'):
                    log.info(line)
            out, err = self.master.vzctl(
                'exec',
                self.config['veid'],
                cmd='chmod 0700 /etc/startup_script')
            if out:
                for line in out.split('\n'):
                    log.info(line)
            if err:
                for line in err.split('\n'):
                    log.info(line)
            out, err = self.master.vzctl(
                'exec',
                self.config['veid'],
                cmd='/etc/startup_script &')
            if out:
                for line in out.split('\n'):
                    log.info(line)
            if err:
                for line in err.split('\n'):
                    log.info(line)
        else:
            log.info("Instance started")
        return True

    def stop(self):
        status = self.vzlist(veid=self.config['veid'])
        if status is None:
            return
        if status['status'] != 'running':
            log.info("Instance state: %s", status['status'])
            log.info("Instance not stopped")
            return
        log.info("Stopping instance '%s'", self.config['veid'])
        self.master.vzctl('stop', self.config['veid'])
        log.info("Instance stopped")

    def terminate(self):
        status = self.vzlist(veid=self.config['veid'])
        if status is None:
            return
        if status['status'] == 'running':
            log.info("Stopping instance '%s'", self.config['veid'])
            self.master.vzctl('stop', self.config['veid'])
            log.info("Instance stopped")
        status = self.vzlist(veid=self.config['veid'])
        if status is None:
            log.error("Unknown instance status")
            log.info("Instance not stopped")
        if status['status'] != 'stopped':
            log.info("Instance state: %s", status['status'])
            log.info("Instance not stopped")
            return
        log.info("Terminating instance '%s'", self.config['veid'])
        self.master.vzctl('destroy', self.config['veid'])
        log.info("Instance terminated")


class Master(BaseMaster):
    sectiongroupname = 'vz-instance'
    instance_class = Instance

    def __init__(self, *args, **kwargs):
        BaseMaster.__init__(self, *args, **kwargs)
        self.instance = PlainInstance(self, self.id, self.master_config)
        self.debug = self.master_config.get('debug-commands', False)

    @lazy
    def vzctl_binary(self):
        binary = ""
        if self.main_config.get('sudo'):
            binary = binary + "sudo "
        binary = binary + self.main_config.get('vzctl', 'vzctl')
        return binary

    @lazy
    def vzlist_binary(self):
        binary = ""
        if self.main_config.get('sudo'):
            binary = binary + "sudo "
        binary = binary + self.main_config.get('vzlist', 'vzlist')
        return binary

    @lazy
    def conn(self):
        from paramiko import SSHException
        try:
            user, host, port, client, known_hosts = self.instance.init_ssh_key()
        except SSHException, e:
            log.error("Couldn't connect to vz-master:%s." % self.id)
            log.error(e)
            sys.exit(1)
        return client

    def _exec(self, cmd, debug=False):
        if debug:
            log.info(cmd)
        rin, rout, rerr = self.conn.exec_command(cmd)
        out = rout.read()
        err = rerr.read()
        if debug and out.strip():
            for line in out.split('\n'):
                log.info(line)
        if debug and err.strip():
            for line in err.split('\n'):
                log.error(line)
        return out, err

    def _vzctl(self, cmd):
        return self._exec("%s %s" % (self.vzctl_binary, cmd), self.debug)

    def _vzlist(self, cmd):
        return self._exec("%s %s" % (self.vzlist_binary, cmd), self.debug)

    def vzctl(self, command, veid, **kwargs):
        if command == 'status':
            out, err = self._vzctl('status %s' % veid)
            out = out.strip().split()
            if out[0] != 'VEID':
                raise ValueError
            if out[0] != 'VEID':
                raise ValueError
            if int(out[1]) != int(veid):
                raise ValueError
            return {
                'exists': out[2],
                'filesystem': out[3],
                'status': out[4]}
        elif command == 'start':
            self._vzctl('start %s' % veid)
        elif command == 'stop':
            self._vzctl('stop %s' % veid)
        elif command == 'destroy':
            self._vzctl('destroy %s' % veid)
        elif command == 'set':
            options = []
            if 'save' in kwargs and kwargs['save']:
                options.append('--save')
            for key in kwargs:
                if not key.startswith('set-'):
                    continue
                options.append("--%s %s" % (key[4:], kwargs[key]))
            options = " ".join(options)
            self._vzctl('set %s %s' % (veid, options))
        elif command == 'exec':
            return self._vzctl('exec %s "%s"' % (veid, kwargs['cmd']))
        elif command == 'create':
            cmd = 'create %s --ostemplate "%s" --ipadd "%s" --hostname "%s"' % (
                veid,
                kwargs['ostemplate'],
                kwargs['ip'],
                kwargs['hostname'])
            out, err = self._vzctl(cmd)
            if err:
                raise OpenVZError(err.strip())
        else:
            raise ValueError("Unknown command '%s'" % command)

    @lazy
    def vzlist_options(self):
        out, err = self._exec("%s -L" % self.vzlist_binary)
        header_map = {}
        option_map = {}
        for line in out.split('\n'):
            line = line.strip()
            if not line:
                continue
            option, header = line.split()
            option_map[option] = header
            if header in header_map:
                continue
            header_map[header] = option
        return header_map, option_map

    def vzlist(self, veid=None, info=None):
        header_map, option_map = self.vzlist_options
        veid_option = header_map[option_map['veid']]
        if info is None:
            info = (veid_option, 'status', 'ip', 'hostname', 'name')
        info = set(info)
        info.add(veid_option)
        unknown = info - set(option_map)
        if unknown:
            raise ValueError("Unknown options in vzlist call: %s" % ", ".join(unknown))
        if veid is None:
            cmd = '-a -o %s' % ','.join(info)
            out, err = self._vzlist(cmd)
            err = err.strip()
        else:
            cmd = '-a -o %s %s' % (','.join(info), veid)
            out, err = self._vzlist(cmd)
            err = err.strip()
        if err == 'Container(s) not found':
            if veid is None:
                return {}
            else:
                return None
        elif err:
            raise ValueError(err)
        lines = out.split('\n')
        headers = [header_map[x] for x in lines[0].split()]
        results = {}
        for line in lines[1:]:
            line = line.strip()
            if not line:
                continue
            values = dict(zip(headers, line.split()))
            results[values[veid_option]] = values
            del values[veid_option]
        if veid is not None:
            return results[str(veid)]
        return results


def get_massagers():
    massagers = []

    sectiongroupname = 'vz-instance'
    massagers.extend([
        IntegerMassager(sectiongroupname, 'veid'),
        UserMassager(sectiongroupname, 'user'),
        PathMassager(sectiongroupname, 'fabfile'),
        StartupScriptMassager(sectiongroupname, 'startup_script')])

    sectiongroupname = 'vz-master'
    massagers.extend([
        UserMassager(sectiongroupname, 'user'),
        BooleanMassager(sectiongroupname, 'sudo'),
        BooleanMassager(sectiongroupname, 'debug-commands')])

    return massagers


def get_masters(main_config):
    masters = main_config.get('vz-master', {})
    for master, master_config in masters.iteritems():
        yield Master(main_config, master, master_config)
