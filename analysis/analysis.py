import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import pdb
from collections import OrderedDict

def clean_xy(x,y):
    new_x = []
    new_y = []
    assert len(x)==len(y)
    for i in range(len(y)):
        if len(y[i]) > 0:
            new_x.append(x[i])
            new_y.append(y[i])
    return new_x, new_y

def error_plot(runs):
    lengend_dict = {'nnet':'neural-net', 'rightinv_pi_fx':"parametric-inverse", 'rightinv_pi_domain':"parametric-inverse-domain"}
    accum_runs = accumulate_runs(runs, 'std_loss_hists')
    line_style = {'nnet':'r--', 'rightinv_pi_fx':'b', 'rightinv_pi_domain':"g"}
    edge_color = {'nnet':'r', 'rightinv_pi_fx':'b', 'rightinv_pi_domain':"g"}
    legend = []
    for algo, v in accum_runs['std_loss_hists'].items():
        x = list(v.keys())
        y = list(v.values())
        x, y = clean_xy(x, y)
        y_upper = list(map(lambda x: np.percentile(x, 75), y))
        y_lower = list(map(lambda x: np.percentile(x, 25), y))
        y_median = list(map(np.median, y))
        plt.semilogy(x, y_median, line_style[algo], label=lengend_dict[algo])
        plt.semilogy(x, y_upper, line_style[algo])
        plt.semilogy(x, y_lower, line_style[algo])
        plt.fill_between(x, y_upper, y_lower, alpha=0.5, edgecolor=edge_color[algo], facecolor=edge_color[algo])
        # legend.append("")
        # legend.append(algo)
        # legend.append("")

    plt.legend(loc='upper right')
    plt.ylabel('Error - |f(x) - y|')
    plt.xlabel('Time (s)')

def full_suite_analysis(runs):
    pass

# Average over many runs
# Make it into a line plot instead of histogram
def update_accum(accum, loss_type, algo, t, batch_loss):
    if loss_type not in accum:
        accum[loss_type] = {}

    if algo not in accum[loss_type]:
        accum[loss_type][algo] = OrderedDict()

    if t in accum[loss_type][algo]:
        accum[loss_type][algo][t] = np.concatenate([accum[loss_type][algo][t], batch_loss])
    else:
        accum[loss_type][algo][t] = batch_loss

    if t > len(accum[loss_type][algo]) - 1:
        for i in range(t - (len(accum[loss_type][algo]) - 1)):
            ar = np.array([])
            accum[loss_type][algo].append(ar)

def accumulate_runs(runs, hist_type):
    accum = {} # std_loss_hist => data

    for run in runs:
        std_loss_hist = run[hist_type]
        for algo, result in std_loss_hist.items():
            print('algo', algo, 'nsteps=', len(result))
            for t, batch_loss in result.items():
                # 'std_loss_hists']['algo'][t].append(batch_loss)
                update_accum(accum, hist_type, algo, t, batch_loss)

    return accum

def plot(runs, total_time, max_error=None):
    std_loss_hists = accumulate_runs(runs, 'std_loss_hists')['std_loss_hists']
    domain_loss_hists = accumulate_runs(runs, 'domain_loss_hists')['domain_loss_hists']

    import matplotlib.pyplot as plt
    import pi
    for k, v in std_loss_hists.items():
        rf.analysis.profile2d(v, total_time, max_error=max_error)
        plt.title('std_loss %s' % k)
        plt.figure()

    for k, v in domain_loss_hists.items():
        rf.analysis.profile2d(v, total_time, max_error=max_error)
        plt.title('domain_loss %s' % k)
        plt.figure()

def cumfreq(a, numbins=10, defaultreallimits=None):
    # docstring omitted
    h,l,b,e = np.histogram(a,numbins,defaultreallimits)
    cumhist = np.cumsum(h*1, axis=0)
    return cumhist,l,b,e

def plot_cdf(data, num_bins):
    counts, bin_edges = np.histogram(data, bins=num_bins, density=True)
    cdf = np.cumsum(counts)
    print(cdf)
    plt.plot(bin_edges[1:], cdf)


def sort_plot(data):
    data = np.sort(data)
    plt.plot(data, np.arange(len(data))/len(data))

def plot_cdfs(loss_hist, t, num_bins=100):
    legend = []
    for k, v in loss_hist.items():
        data = loss_hist[k][t]
        data = np.sort(data)
        plt.semilogx(data, np.arange(len(data))/len(data))
        legend.append(k)

    plt.legend(legend, loc='upper left')
    plt.ylabel('Count')
    plt.xlabel('Domain Error - f(x*)')


def profile2d(x,  total_time, ybins=20, max_error=None, cumulative=True):
    """
    Plot a histogram of error vs number of examples
    """
    if max_error is None:
        max_error = np.max(np.concatenate(list(x.values())))

    print("MAX_ERRPR", max_error)
    print("here")
    if np.isinf(max_error):
        max_error = None
    if np.isnan(max_error):
        return False
    xbins = len(x)
    img = np.random.rand(ybins, xbins)
    for k, v in x.items():
        bincount, bin_edges = np.histogram(v, bins=ybins,
                                           range=(0.0, max_error))
        if cumulative:
            bincount = np.cumsum(bincount)
        for j, count in enumerate(bincount):
            img[j, k] = count

    # the histogram of the data
    result = plt.imshow(img, extent=[0, total_time, 0, max_error], aspect='auto')
    # l = plt.plot(bins)
    plt.ylabel('Error - |f(x*) - x|')
    plt.xlabel('Time (s)')
    plt.colorbar()
    return result, img


def profile(x, bins=20, cumulative=True, histtype='step', **kwargs):
    """
    Plot a histogram of error vs number of examples
    """
    # the histogram of the data
    result = plt.hist(x, bins=bins, cumulative=True,
                                histtype=histtype,
                                alpha=0.75, **kwargs)
    l = plt.plot(bins)
    plt.xlabel('Error - |f(x*) - x|')
    plt.ylabel('Examples per second')
    return l
