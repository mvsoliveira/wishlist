import os
import pandas as pd
pd.options.plotting.backend = "plotly"
from multiprocessing import Pool
from functools import partial
import re
from pathlib import Path
import glob
import logging
logging.basicConfig(format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s', datefmt='%Y-%m-%d %H:%M:%S')


# Function outside the class to allow multithreading
def generate_plot(col, run, larc, df, vec_index0_regex, vec_indexany_regex, plot_vector_items):
    def _generate_plot(col, run, larc, df, name,showlegend):
        fig = df[col].plot(template="plotly_white",
                           # title=f'{larc} - {run}'
                           labels=dict(index="Time", value=name,variable='Vector items'))
        # hovermode='x' is used to ensure good browsing performance with large datasets
        fig.update_layout(showlegend=showlegend, hovermode="x")
        fig.write_html(f'../www/{run}/{larc}/{name}.html', include_plotlyjs='directory')

    if 'int' or 'float' in df[col].dtypes.name:
        if pd.options.plotting.backend == 'plotly':
            if vec_index0_regex.search(col):
                name = vec_index0_regex.sub("\\1\\2\\3\\4",col)
                vec_cols = [f'{name}[{index}]' for index in range(int(list(vec_index0_regex.finditer(col))[0].groupdict()['size']))]
                _generate_plot(vec_cols,run,larc,df,name, True)
            if plot_vector_items or not vec_indexany_regex.search(col):
                _generate_plot(col, run, larc, df, col, False)



class Pandas2Plot(object):
    def __init__(self,
                 plot_threads,
                 plot_vector_items,
                 partition='ATLAS',
                 larc='LArC_EMBA_1',
                 start='2022-03-08 16:30:00',
                 stop='2022-03-08 16:40:00',
                 run='current',
                 load_pickle='',
                 save_pickle='is2pandas.pickle',
                 **kwargs):
        self.plot_threads = plot_threads
        self.plot_vector_items = plot_vector_items
        self.vec_index0_regex = re.compile(r"(?P<base>[\.\w]+)(\()(?P<size>\d+)(\))(\(0\))")
        self.vec_indexany_regex = re.compile(r"(?P<base>[\.\w]+)(\()(?P<size>\d+)(\))(\(\d+\))")
        self.link_template = '<a href = "<VARIABLE>.html" target = "main"><VARIABLE></a><br>\n'
        self.link__vector_item_template = '<a href = "<VARIABLE>.html" target = "main"><VARIABLE></a>\n'
        self.link_vector_template = '<button onclick="showhide(\'<VARIABLE>\')" id=<VARIABLE>_b>+</button><br>\n<p hidden id="<VARIABLE>">\n<LINKS_VECTOR_ITEMS></p>'
        self.reading_template('../templates/links_template')
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

    def wanted_variable(self, variable):
        for regex in self.wanted_variable_regexes_compiled:
            if regex.search(variable):
                return True
        return False

    def action(self):
        Path(f'../www').mkdir(parents=True, exist_ok=True)
        Path(f'../pickle').mkdir(parents=True, exist_ok=True)
        self.get_data_from_server()
        df_list = []
        for file in glob.glob('../pickle/*.pickle'):
            df_list.append(pd.read_pickle(file))
        self.df = pd.concat(df_list)
        self.df.sort_index(inplace=True)
        self.generating_plots()
        self.generating_html()

    def get_data_from_server(self):
        os.system(f'rsync --remove-source-files -zvhL zynq-p1.cern.ch:/software/tmp/* ../pickle/')

    def generating_plots(self):
        self.lgr.info(f'Generating plots for {self.larc}')
        gen_plot = partial(generate_plot, run=self.run, larc=self.larc, df=self.df, vec_index0_regex=self.vec_index0_regex,vec_indexany_regex=self.vec_indexany_regex,plot_vector_items=self.plot_vector_items)
        if self.plot_threads == 1:
            for col in self.df.columns:
                gen_plot(col)
        else:
            with Pool() as p:
                p.map(gen_plot, self.df.columns)

    def reading_template(self, name):
        with open(f'{name}.html', 'r') as f:
            setattr(self,name.split('/')[-1],f.read())

    def write_str(self, string, filepath):
        with open(filepath, 'w') as f:
            f.write(string)

    def generating_html(self):
        self.lgr.info(f'Generating pages for {self.larc}.')
        links = ''
        for col in self.df.columns:
            if self.vec_indexany_regex.search(col): # Is it a vector?
                if self.vec_index0_regex.search(col): # Is it the item 0 of a vector?
                    name = self.vec_index0_regex.sub("\\1\\2\\3\\4", col)
                    links += self.link__vector_item_template.replace('<VARIABLE>', name)
                    if self.plot_vector_items: # Should we print the vector sub items?
                        vec_cols = [self.link__vector_item_template.replace('<VARIABLE>', f'{name}[{index}]') for index in
                                    range(int(list(self.vec_index0_regex.finditer(col))[0].groupdict()['size']))]
                        link_vector_items = '<br>'.join(vec_cols)
                        links += self.link_vector_template.replace('<VARIABLE>', name).replace('<LINKS_VECTOR_ITEMS>',link_vector_items)
            else: # Well it is not a vector
                links += self.link_template.replace('<VARIABLE>',col).replace("<TARGET>",'main')
        if not links: links = f'<center>No data from {self.larc} have been found between<br>{self.start} and {self.stop}.<br><br>Either LAr was not running in the ATLAS partition or this LArC was not included.<br>Try selecting another LArC or a different time range.</center>'
        links_html = self.links_template.replace('<LINKS>',links)
        self.write_str(f'<h3>{self.larc}</h3>{links_html}',f'../www/{self.run}/{self.larc}/menu.html')
        os.system(f'cd ../www/{self.run}/{self.larc}; ln -fs ../../perlarc_index.html index.html')


if __name__ == '__main__':
    larc = 'LArC_EMBA_2'
    wanted_variable_regexes = ('bcid_calibration', 'freq', 'counter\[0\]', 'bcr_err', 'period', 'bitslip', 'reset_clock',)
    #wanted_variable_regexes = ('freq', 'counter\[0\]', 'bcr_err', 'period',)
    pandas2plot = Pandas2Plot(larc=larc,run='current', plot_threads=1,plot_vector_items=True, wanted_variable_regexes = wanted_variable_regexes)