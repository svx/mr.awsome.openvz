from StringIO import StringIO
from mock import patch
from mr.awsome import AWS
from unittest2 import TestCase
import os
import tempfile
import shutil


vzlist_output = """\
veid            VEID           
vpsid           VEID           
hostname        HOSTNAME       
name            NAME           
ip              IP_ADDR        
status          STATUS         
kmemsize        KMEMSIZE       
kmemsize.m      KMEMSIZE.M     
kmemsize.b      KMEMSIZE.B     
kmemsize.l      KMEMSIZE.L     
kmemsize.f      KMEMSIZE.F     
lockedpages     LOCKEDP        
lockedpages.m   LOCKEDP.M      
lockedpages.b   LOCKEDP.B      
lockedpages.l   LOCKEDP.L      
lockedpages.f   LOCKEDP.F      
privvmpages     PRIVVMP        
privvmpages.m   PRIVVMP.M      
privvmpages.b   PRIVVMP.B      
privvmpages.l   PRIVVMP.L      
privvmpages.f   PRIVVMP.F      
shmpages        SHMP           
shmpages.m      SHMP.M         
shmpages.b      SHMP.B         
shmpages.l      SHMP.L         
shmpages.f      SHMP.F         
numproc         NPROC          
numproc.m       NPROC.M        
numproc.b       NPROC.B        
numproc.l       NPROC.L        
numproc.f       NPROC.F        
physpages       PHYSP          
physpages.m     PHYSP.M        
physpages.b     PHYSP.B        
physpages.l     PHYSP.L        
physpages.f     PHYSP.F        
vmguarpages     VMGUARP        
vmguarpages.m   VMGUARP.M      
vmguarpages.b   VMGUARP.B      
vmguarpages.l   VMGUARP.L      
vmguarpages.f   VMGUARP.F      
oomguarpages    OOMGUARP       
oomguarpages.m  OOMGUARP.M     
oomguarpages.b  OOMGUARP.B     
oomguarpages.l  OOMGUARP.L     
oomguarpages.f  OOMGUARP.F     
numtcpsock      NTCPSOCK       
numtcpsock.m    NTCPSOCK.M     
numtcpsock.b    NTCPSOCK.B     
numtcpsock.l    NTCPSOCK.L     
numtcpsock.f    NTCPSOCK.F     
numflock        NFLOCK         
numflock.m      NFLOCK.M       
numflock.b      NFLOCK.B       
numflock.l      NFLOCK.L       
numflock.f      NFLOCK.F       
numpty          NPTY           
numpty.m        NPTY.M         
numpty.b        NPTY.B         
numpty.l        NPTY.L         
numpty.f        NPTY.F         
numsiginfo      NSIGINFO       
numsiginfo.m    NSIGINFO.M     
numsiginfo.b    NSIGINFO.B     
numsiginfo.l    NSIGINFO.L     
numsiginfo.f    NSIGINFO.F     
tcpsndbuf       TCPSNDB        
tcpsndbuf.m     TCPSNDB.M      
tcpsndbuf.b     TCPSNDB.B      
tcpsndbuf.l     TCPSNDB.L      
tcpsndbuf.f     TCPSNDB.F      
tcprcvbuf       TCPRCVB        
tcprcvbuf.m     TCPRCVB.M      
tcprcvbuf.b     TCPRCVB.B      
tcprcvbuf.l     TCPRCVB.L      
tcprcvbuf.f     TCPRCVB.F      
othersockbuf    OTHSOCKB       
othersockbuf.m  OTHSOCKB.M     
othersockbuf.b  OTHSOCKB.B     
othersockbuf.l  OTHSOCKB.L     
othersockbuf.f  OTHSOCKB.F     
dgramrcvbuf     DGRAMRB        
dgramrcvbuf.m   DGRAMRB.M      
dgramrcvbuf.b   DGRAMRB.B      
dgramrcvbuf.l   DGRAMRB.L      
dgramrcvbuf.f   DGRAMRB.F      
numothersock    NOTHSOCK       
numothersock.m  NOTHSOCK.M     
numothersock.b  NOTHSOCK.B     
numothersock.l  NOTHSOCK.L     
numothersock.f  NOTHSOCK.F     
dcachesize      DCACHESZ       
dcachesize.m    DCACHESZ.M     
dcachesize.b    DCACHESZ.B     
dcachesize.l    DCACHESZ.L     
dcachesize.f    DCACHESZ.F     
numfile         NFILE          
numfile.m       NFILE.M        
numfile.b       NFILE.B        
numfile.l       NFILE.L        
numfile.f       NFILE.F        
numiptent       NIPTENT        
numiptent.m     NIPTENT.M      
numiptent.b     NIPTENT.B      
numiptent.l     NIPTENT.L      
numiptent.f     NIPTENT.F      
diskspace       DQBLOCKS       
diskspace.s     DQBLOCKS.S     
diskspace.h     DQBLOCKS.H     
diskinodes      DQINODES       
diskinodes.s    DQINODES.S     
diskinodes.h    DQINODES.H     
laverage        LAVERAGE       
cpulimit        CPULIM         
cpuunits        CPUUNI         
"""


class OpenVZSetupTests(TestCase):
    def setUp(self):
        self.directory = tempfile.mkdtemp()
        self.aws = AWS(self.directory)
        self._ssh_client_mock = patch("ssh.SSHClient")
        self.ssh_client_mock = self._ssh_client_mock.start()
        self._ssh_config_mock = patch("ssh.SSHConfig")
        self.ssh_config_mock = self._ssh_config_mock.start()
        self.ssh_config_mock().lookup.return_value = {}
        self._subprocess_call_mock = patch("subprocess.call")
        self.subprocess_call_mock = self._subprocess_call_mock.start()

    def tearDown(self):
        self.subprocess_call_mock = self._subprocess_call_mock.stop()
        del self.subprocess_call_mock
        self.ssh_config_mock = self._ssh_config_mock.stop()
        del self.ssh_config_mock
        self.ssh_client_mock = self._ssh_client_mock.stop()
        del self.ssh_client_mock
        shutil.rmtree(self.directory)
        del self.directory

    def _write_config(self, content):
        with open(os.path.join(self.directory, 'aws.conf'), 'w') as f:
            f.write('\n'.join([
                '[plugin:vz]',
                'module = mr.awsome.openvz']))
            f.write('\n')
            f.write(content)

    def testNoVeid(self):
        self._write_config('\n'.join([
            '[vz-master:default]',
            '[vz-instance:foo]']))
        with patch('mr.awsome.openvz.log') as LogMock:
            with self.assertRaises(SystemExit):
                self.aws(['./bin/aws', 'status', 'foo'])
        LogMock.error.assert_called_with("No veid set in vz-instance:%s.", 'foo')

    def testNoHostSetOnMaster(self):
        self._write_config('\n'.join([
            '[vz-master:default]',
            '[vz-instance:foo]',
            'veid = 101']))
        with patch('mr.awsome.openvz.log') as LogMock:
            with self.assertRaises(SystemExit):
                self.aws(['./bin/aws', 'status', 'foo'])
        self.assertEquals(
            LogMock.error.call_args_list, [
                (("Couldn't connect to vz-master:default.",), {}),
                ((u'No host set in config.',), {})])

    def testNoFingerprintSetOnMaster(self):
        self._write_config('\n'.join([
            '[vz-master:default]',
            'host = localhost',
            '[vz-instance:foo]',
            'veid = 101']))
        with patch('mr.awsome.openvz.log') as LogMock:
            with self.assertRaises(SystemExit):
                self.aws(['./bin/aws', 'status', 'foo'])
        self.assertEquals(
            LogMock.error.call_args_list, [
                (("Couldn't connect to vz-master:default.",), {}),
                ((u'No fingerprint set in config.',), {})])


class OpenVZTests(TestCase):
    def setUp(self):
        self.directory = tempfile.mkdtemp()
        self.aws = AWS(self.directory)
        self._ssh_client_mock = patch("ssh.SSHClient")
        self.ssh_client_mock = self._ssh_client_mock.start()
        self.ssh_client_exec_results = []
        def exec_command(cmd):
            if len(self.ssh_client_exec_results) == 0: # pragma: no cover - only if test is wrong
                self.fail("No results for exec_command, expected on for '%s'" % cmd)
            result = self.ssh_client_exec_results.pop(0)
            if len(result) != 2 or len(result[1]) != 2: # pragma: no cover - only if test is wrong
                self.fail("ssh_client_exec_results needs to contain tuples in the form of (expected_cmd, (stdout, stderr)).")
            self.assertEquals(cmd, result[0], 'expected command mismatch')
            return None, StringIO(result[1][0]), StringIO(result[1][1])
        self.ssh_client_mock().exec_command.side_effect = exec_command
        self._ssh_config_mock = patch("ssh.SSHConfig")
        self.ssh_config_mock = self._ssh_config_mock.start()
        self.ssh_config_mock().lookup.return_value = {}
        self._subprocess_call_mock = patch("subprocess.call")
        self.subprocess_call_mock = self._subprocess_call_mock.start()

    def tearDown(self):
        self.subprocess_call_mock = self._subprocess_call_mock.stop()
        del self.subprocess_call_mock
        self.ssh_config_mock = self._ssh_config_mock.stop()
        del self.ssh_config_mock
        self.ssh_client_mock = self._ssh_client_mock.stop()
        del self.ssh_client_mock
        shutil.rmtree(self.directory)
        del self.directory

    def _write_config(self, content):
        with open(os.path.join(self.directory, 'aws.conf'), 'w') as f:
            f.write('\n'.join([
                '[plugin:vz]',
                'module = mr.awsome.openvz',
                '[vz-master:default]',
                'host = localhost',
                'fingerprint = foo']))
            f.write('\n')
            f.write(content)

    def testOldVzlistUnkownVE(self):
        self._write_config('\n'.join([
            '[vz-instance:foo]',
            'veid = 101']))
        self.ssh_client_exec_results.append((
            'vzlist -L',
            (vzlist_output, '')))
        self.ssh_client_exec_results.append((
            'vzlist -a -o status,ip,hostname,veid,name 101',
            ('', 'VE not found')))
        with patch('mr.awsome.openvz.log') as LogMock:
            try:
                self.aws(['./bin/aws', 'status', 'foo'])
            except SystemExit: # pragma: no cover - only if something is wrong
                self.fail("SystemExit raised")
        self.assertEquals(
            LogMock.info.call_args_list, [
                (("Instance '%s' (%s) unavailable", 'foo', 101), {})])

    def testUnkownContainer(self):
        self._write_config('\n'.join([
            '[vz-instance:foo]',
            'veid = 101']))
        self.ssh_client_exec_results.append((
            'vzlist -L',
            (vzlist_output, '')))
        self.ssh_client_exec_results.append((
            'vzlist -a -o status,ip,hostname,veid,name 101',
            ('', 'Container(s) not found')))
        with patch('mr.awsome.openvz.log') as LogMock:
            try:
                self.aws(['./bin/aws', 'status', 'foo'])
            except SystemExit: # pragma: no cover - only if something is wrong
                self.fail("SystemExit raised")
        self.assertEquals(
            LogMock.info.call_args_list, [
                (("Instance '%s' (%s) unavailable", 'foo', 101), {})])

    def testFoo(self):
        self._write_config('\n'.join([
            '[vz-instance:foo]',
            'veid = 101']))
        self.ssh_client_exec_results.append((
            'vzlist -L',
            (vzlist_output, '')))
        self.ssh_client_exec_results.append((
            'vzlist -a -o status,ip,hostname,veid,name 101', (
                "STATUS  IP_ADDR         HOSTNAME                               VEID NAME\n"
                "running 10.0.0.1        foo.example.com                         101 -", '')))
        with patch('mr.awsome.openvz.log') as LogMock:
            try:
                self.aws(['./bin/aws', 'status', 'foo'])
            except SystemExit: # pragma: no cover - only if something is wrong
                self.fail("SystemExit raised")
        self.assertEquals(
            LogMock.info.call_args_list, [
                (('Instance running.',), {}),
                (('Instances host name %s', 'foo.example.com'), {}),
                (('Instances ip address %s', '10.0.0.1'), {})])
