from Pandas2Plot import *
from multiprocessing import Pool
from datetime import datetime,timedelta


# Function outside the class to allow multithreading
def create_Pandas2Plot(larc, plot_threads, plot_vector_items, partition, start, stop, run, load_pickle, save_pickle,
                       wanted_variable_regexes):
    pandas2plot = Pandas2Plot(larc=larc,
                plot_threads=plot_threads,
                plot_vector_items=plot_vector_items,
                partition=partition,
                start=start,
                stop=stop,
                run=run,
                load_pickle=load_pickle,
                save_pickle=save_pickle,
                wanted_variable_regexes=wanted_variable_regexes,
                )
    pandas2plot.action()

class MultiPandas2Plot(Pandas2Plot):
    def __init__(self,larcs,larc_threads,**kwargs):
        super().__init__(**kwargs)
        self.larcs = larcs
        self.larc_threads = larc_threads
        self.menu_fmt = '<html>\n<table style="width:100%">\n<tr>\n<td>\n<a href="../../index.html" target="_top"><img src="../larisplot_small.png" width="40%" height="40%"></a></td>\n{cols:s}\n</tr>\n</table>\n</html>'
        self.menu_col_fmt = '\n<td>{col:s}</td>'
        self.menu_row_fmt = '<a href = "{link:s}" target = "{target:s}">{name:s}</a><br>\n'

    def action(self):
        # dont generate larc menu and keep the one generated under www
        #self.write_menu_table(f'../www/{self.run}/larc_menu.html', self.larcs, target='main_top',
                              #link_fmt='{item:s}/index.html', max_row=5)
        os.system(f'cd ../www/{self.run}/; ln -fs ../perrun_index.html index.html')
        os.system(f'cd ../www/{self.run}/; ln -fs ../larc_menu.html larc_menu.html')

        cre_Pandas2Plot = partial(create_Pandas2Plot, plot_threads=self.plot_threads,
                                  plot_vector_items=self.plot_vector_items, partition=self.partition,
                                  start=self.start, stop=self.stop, run=self.run, load_pickle=self.load_pickle,
                                  save_pickle=self.save_pickle, wanted_variable_regexes=None)
        # Multi and single threads calls
        if self.larc_threads == 1:
            for lar in self.larcs:
                cre_Pandas2Plot(lar)
        elif 1 <= self.larc_threads <= 5:
            if self.plot_threads == 1:
                with Pool(self.larc_threads) as p:
                    p.map(cre_Pandas2Plot, self.larcs)
            else:
                self.lgr.fatal('Plot and LArC multithreading can not coexist because daemonic processes are not allowed to have children. If many IS variables are wanted, opt for plot multithreading by setting plot threads to None and larc threads to 1.')
        else:
            self.lgr.fatal('LArC Threads has to be from 1 to 5. The PBeast server drops requests if more than 5 queries are submitted simultaneously.')

    def write_menu_table(self, filepath, items, target, link_fmt='{item:s}.html}', max_row=2):
        cols = ''
        col = ''
        for i, item in enumerate(items):
            link = link_fmt.format(item=item)
            col += self.menu_row_fmt.format(link=link, target=target, name=item)
            if i % max_row == (max_row - 1):
                cols += self.menu_col_fmt.format(col=col)
                col = ''
        cols += self.menu_col_fmt.format(col=col)
        self.write_str(self.menu_fmt.format(cols=cols), filepath)




if __name__ == '__main__':

    larcs = ['gfex-production-stf']

    now = datetime.now()
    stop = now.strftime("%Y-%m-%d %H:%M:%S")
    start = (now - timedelta(seconds=60*30)).strftime("%Y-%m-%d %H:%M:%S")

    start = '2022-05-31 12:00:00'
    stop = '2022-05-31 24:00:00'
    wanted_variable_regexes = None


    multipandas2plot = MultiPandas2Plot(larcs,
                                        larc_threads = 1,
                                        plot_threads=None,
                                        plot_vector_items=True,
                                        partition='ATLAS',
                                        start=start,
                                        stop=stop,
                                        run='P1_December13th',
                                        load_pickle='',
                                        save_pickle='',
                                        wanted_variable_regexes=wanted_variable_regexes)

    multipandas2plot.action()
