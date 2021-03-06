from os.path import dirname, basename, expanduser, exists, splitext
from os import makedirs
from matplotlib import pyplot as plt
from math import log10
import warnings
import numpy as np
from traitlets import Dict, List, Unicode, Int, Bool
from ctapipe.core import Tool, Component
from ctapipe.analysis.camera.chargeresolution import ChargeResolutionCalculator


class ChargeResolutionPlotter(Component):
    name = 'ChargeResolutionPlotter'

    output_path = Unicode(None, allow_none=True,
                          help='Output path to save the '
                               'plot.').tag(config=True)
    max_pe = Int(2000, help='Maximum pe to plot').tag(config=True)
    linear_x = Bool(False, help='Plot the x values on a linear axis, '
                                'instead of log').tag(config=True)
    linear_y = Bool(False, help='Plot the y values on a linear axis, '
                                'instead of log').tag(config=True)

    def __init__(self, config, tool, **kwargs):
        """
        Calculator of charge resolution.

        Parameters
        ----------
        config : traitlets.loader.Config
            Configuration specified by config file or cmdline arguments.
            Used to set traitlet values.
            Set to None if no configuration to pass.
        tool : ctapipe.core.Tool
            Tool executable that is calling this component.
            Passes the correct logger to the component.
            Set to None if no Tool to pass.
        reductor : ctapipe.calib.camera.reductors.Reductor
            The reductor to use to reduce the waveforms in the event.
            By default no data volume reduction is applied, and the dl0 samples
            will equal the r1 samples.
        kwargs
        """
        super().__init__(config=config, parent=tool, **kwargs)

        try:
            if self.output_path is None:
                raise ValueError
        except ValueError:
            self.log.exception('Please specify an output path')
            raise

        self.fig = plt.figure(figsize=(20, 8))
        self.ax_l = self.fig.add_subplot(121)
        self.ax_r = self.fig.add_subplot(122)

        self.fig.subplots_adjust(left=0.05, right=0.95, wspace=0.6)

        self.legend_handles = []
        self.legend_labels = []

    def plot_chargeres(self, name, x, res, error):
        valid = (x <= self.max_pe)
        x_v = x[valid]
        res_v = res[valid]
        error_v = error[valid]

        eb_l, _, _ = self.ax_l.errorbar(x_v, res_v, yerr=error_v,
                                        marker='x', linestyle="None")
        self.legend_handles.append(eb_l)
        self.legend_labels.append(splitext(name)[0])

    def plot_scaled_chargeres(self, x, res, error):
        valid = (x <= self.max_pe)
        x_v = x[valid]
        res_v = res[valid]
        error_v = error[valid]

        self.ax_r.errorbar(x_v, res_v, yerr=error_v,
                           marker='x', linestyle="None")

    def plot_limit_curves(self):
        x = np.logspace(log10(0.9), log10(self.max_pe * 1.1), 100)
        requirement = ChargeResolutionCalculator.requirement(x)
        goal = ChargeResolutionCalculator.goal(x)
        poisson = ChargeResolutionCalculator.poisson(x)

        r_p, = self.ax_l.plot(x, requirement, 'r', ls='--')
        g_p, = self.ax_l.plot(x, goal, 'g', ls='--')
        p_p, = self.ax_l.plot(x, poisson, c='0.75', ls='--')
        self.ax_r.plot(x, requirement / goal, 'r')
        self.ax_r.plot(x, goal / goal, 'g')
        self.ax_r.plot(x, poisson / goal, c='0.75', ls='--')

        self.legend_handles.append(r_p)
        self.legend_labels.append("Requirement")
        self.legend_handles.append(g_p)
        self.legend_labels.append("Goal")
        self.legend_handles.append(p_p)
        self.legend_labels.append("Poisson")

    def save(self):
        if not self.linear_x:
            self.ax_l.set_xscale('log')
            self.ax_r.set_xscale('log')
        if not self.linear_y:
            self.ax_l.set_yscale('log')

        self.ax_l.set_xlabel(r'True Charge $Q_T$ (p.e.)')
        self.ax_l.set_ylabel('Charge Resolution')
        self.ax_r.set_xlabel(r'True Charge $Q_T$ (p.e.)')
        self.ax_r.set_ylabel('Charge Resolution/Goal')

        self.ax_l.legend(self.legend_handles, self.legend_labels,
                         bbox_to_anchor=(1.02, 1.), loc=2,
                         borderaxespad=0., fontsize=10)

        self.fig.suptitle(splitext(basename(self.output_path))[0])

        self.ax_l.set_xlim(0.9, self.max_pe * 1.1)
        self.ax_r.set_xlim(0.9, self.max_pe * 1.1)
        if self.max_pe > 2000:
            self.ax_r.set_xlim(0.9, 2000 * 1.1)
        # if args.maxpeplot is not None:
        #     ax_l.set_xlim(0.9, args.maxpeplot)
        #     ax_r.set_xlim(0.9, args.maxpeplot)

        warnings.filterwarnings("ignore", module="matplotlib")
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            if self.output_path is None:
                plt.show()
            else:
                self.output_path = expanduser(self.output_path)
                output_dir = dirname(self.output_path)
                if not exists(output_dir):
                    self.log.info("[output] Creating directory: "
                                  "{}".format(output_dir))
                    makedirs(output_dir)
                self.log.info("[output] {}".format(self.output_path))
                self.fig.savefig(self.output_path, bbox_inches='tight')


class ChargeResolutionViewer(Tool):
    name = "ChargeResolutionViewer"
    description = "Plot the charge resolution from " \
                  "ChargeResolutionCalculator objects restored via " \
                  "pickled dictionaries."

    input_files = List(Unicode, None,
                       help='Input pickle files that are produced from '
                            'ChargeResolutionCalculator.save().'
                            '').tag(config=True)

    aliases = Dict(dict(f='ChargeResolutionViewer.input_files',
                        B='ChargeResolutionCalculator.binning',
                        max_pe='ChargeResolutionPlotter.max_pe',
                        O='ChargeResolutionPlotter.output_path',
                        ))
    flags = Dict(dict(L=({'ChargeResolutionCalculator': {'log_bins': False}},
                         'Bin the x axis linearly instead of logarithmic.'),
                      linx=({'ChargeResolutionPlotter': {'linear_x': True}},
                            'Plot the x values on a linear axis, '
                            'instead of log.'),
                      liny=({'ChargeResolutionPlotter': {'linear_y': True}},
                            'Plot the x values on a linear axis, '
                            'instead of log.')
                      ))
    classes = List([ChargeResolutionCalculator,
                    ChargeResolutionPlotter
                    ])

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.calculator = None
        self.plotter = None

    def setup(self):
        self.log_format = "%(levelname)s: %(message)s [%(name)s.%(funcName)s]"
        kwargs = dict(config=self.config, tool=self)

        self.calculator = ChargeResolutionCalculator(**kwargs)
        self.plotter = ChargeResolutionPlotter(**kwargs)

    def start(self):
        self.plotter.plot_limit_curves()
        for fp in self.input_files:
            self.calculator.load(fp)
            x, res, res_error, scaled_res, scaled_res_error = \
                self.calculator.get_charge_resolution()

            name = basename(fp)
            self.plotter.plot_chargeres(name, x, res, res_error)
            self.plotter.plot_scaled_chargeres(x, scaled_res, scaled_res_error)

    def finish(self):
        self.plotter.save()


if __name__ == '__main__':
    exe = ChargeResolutionViewer()
    exe.run()
