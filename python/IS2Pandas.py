import subprocess
import shlex
import logging
logging.basicConfig(format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
import pickle
import re
import pandas as pd
from pathlib import Path
from multiprocessing import Process, Manager
from pathlib import Path
class IS2Pandas(object):
    def __init__(self,
                 wanted_variable_regexes=('.+',),
                 partition = 'ATLAS',
                 larc='LArC_EMBA_1',
                 start='2022-03-08 16:30:00',
                 stop='2022-03-08 16:40:00',
                 run='current',
                 load_pickle='',
                 save_pickle='is2pandas.pickle',
                 ):
        # logging
        self.lgr = logging.getLogger(self.__class__.__name__)
        self.lgr.setLevel(logging.DEBUG)
        # Internals
        self.partition = partition
        self.larc = larc
        self.run = run
        self.start = start
        self.stop = stop
        self.load_pickle = load_pickle
        self.save_pickle = save_pickle
        Path(f'../www/{self.run}/{self.larc}/').mkdir(parents=True, exist_ok=True)

    def reading_pbeast(self):
        self.lgr.info(f'Reading archived data from {self.larc} between {self.start} and {self.stop}. Saving results at "{self.run}" folder.')
        #command = f'source /det/lar/project/scripts/env/sod.sh>/dev/null;/sw/atlas/tdaq/tdaq-09-04-00/installed/x86_64-centos7-gcc11-opt/bin/pbeast_read_server --server-name pbeast-server  -p ATLAS  -c String  -s "2022-03-04 11:10:00" -t "2022-03-04 12:20:00" -z Europe/Zurich -a value -O "{self.object_regex:s}"'
        command = f'source /cvmfs/atlas.cern.ch/repo/sw/tdaq/tdaq/tdaq-09-04-00/installed/setup.sh>/dev/null;PBEAST_SERVER_SSO_SETUP_TYPE=autoupdatekerberos pbeast_read -p {self.partition} -n "https://atlasop.cern.ch"  -c String -a value -s "{self.start}" -t "{self.stop}" -z Europe/Zurich  -O "{self.object_regex:s}"'
        sh = "/bin/sh -c"
        cmd = shlex.split(sh)
        cmd.append(command)

        if self.load_pickle:
            with open(self.load_pickle, 'rb') as f:
                self.lgr.info(f'Loading: {self.load_pickle}.')
                self.pbeast_out = pickle.load(f)
        else:
            self.lgr.info("Executing command: {cmd:s}".format(cmd=' '.join(cmd)))
            self.pbeast_out = subprocess.run(cmd, stdout=subprocess.PIPE).stdout.decode('utf-8')
            if self.save_pickle:
                with open(self.save_pickle, 'wb') as f:
                    pickle.dump(self.pbeast_out, f)

    def wanted_variable(self,variable):
        for regex in self.wanted_variable_regexes_compiled:
            if regex.search(variable):
                return True
        return False

    def isstring2pandas(self,flattening=True, save_html='../www/df.html'):
        self.lgr.info(f'Generating Pandas dataframe for {self.larc}.')
        time_regex = r"\[(?P<time>.+CES?T)\]\s\"(?P<is>.+)\""
        variable_regex = r"<(?P<name>[\w\.\[\]\d]+)>\s(?P<value>[^<]+)"
        # Finding each time LDPB updated values
        time_matches = re.finditer(time_regex, self.pbeast_out, re.MULTILINE)
        df = pd.DataFrame()
        self.append_data = []
        for time_matchNum, time_match in enumerate(time_matches, start=1):
            # Finding each variable
            variable_matches = re.finditer(variable_regex, time_match.groupdict()['is'], re.MULTILINE)
            variables = {}
            for variable_matchNum, variable_match in enumerate(variable_matches, start=1):
                # Propagating to Data Frame only wanted variables, checking parse_all to speed-up
                if self.parse_all or self.wanted_variable(variable_match.groupdict()['name']):
                    # Decides if vectors are flattened into different scalar entries
                    if flattening:
                        # Finding each entry of an array
                        for id,value in enumerate(variable_match.groupdict()['value'].strip().split(' ')):
                            variables[variable_match.groupdict()['name']+f'[{id}]'] = value
                    else:
                        variables[variable_match.groupdict()['name']] = variable_match.groupdict()['value'].strip().split(' ')
            self.append_data.append(pd.DataFrame(variables, index=[time_match.groupdict()['time']]))
        self.lgr.debug(f'Concatenating dataframes for {self.larc}.')
        df = pd.concat(self.append_data)
        self.lgr.debug(f'Casting row to a numeric type whenever possible for {self.larc}.')
        for col in df.columns:
            df[col] = pd.to_numeric(df[col],errors='ignore')
        if save_html:
            self.lgr.info(f'writing {save_html}.')
            df.to_html(save_html)
        self.df = df





if __name__ == '__main__':
    is2pandas = IS2Pandas(load_pickle='is2pandas.pickle')
    is2pandas.isstring2pandas(save_html=False)

    #is2pandas = IS2Pandas()
