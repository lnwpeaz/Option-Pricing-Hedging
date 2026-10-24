"""Static research figures; raw tables retain every method/cell and failure."""
import math
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

COLORS={'plain':'#64748b','antithetic':'#e69f00','control':'#009e73','sobol':'#0072b2','sobol_bridge':'#cc79a7'}


def create_figures(out,metrics,references,bench,allocations):
    plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False,'figure.facecolor':'white'})
    contracts=list(references.itertuples());cols=min(3,len(contracts));rows=math.ceil(len(contracts)/cols)
    for name in ['accuracy','calibration']:
        fig,axes=plt.subplots(rows,cols,figsize=(max(12,5*cols),max(5,3.7*rows)),squeeze=False)
        for ax,ref in zip(axes.flat,contracts):
            group=metrics[metrics.contract_id==ref.contract_id]
            for method,m in group.groupby('method',sort=False):
                m=m.sort_values('n_paths');x=m.n_paths.to_numpy();color=COLORS[method]
                if name=='accuracy':
                    y=m.rmse.to_numpy(dtype=float)
                    valid=np.isfinite(y)&(y>0)
                    ax.plot(x[valid],y[valid],marker='o',color=color,label=method)
                    low=m.bootstrap_rmse_low.to_numpy(dtype=float);high=m.bootstrap_rmse_high.to_numpy(dtype=float)
                    ok=valid&np.isfinite(low)&np.isfinite(high)&(low>0)
                    ax.fill_between(x[ok],low[ok],high[ok],alpha=.10,color=color)
                else:
                    ax.plot(x,m.possible_coverage,color=color,marker='o',label=method)
                    ax.plot(x,m.definite_coverage,color=color,linestyle=':',marker='x')
            ax.set_title(f'{ref.fixing_count} fixings | K={ref.strike:g}')
            ax.set_xscale('log',base=2);ax.set_xlim(float(group.n_paths.min())*.8,float(group.n_paths.max())*1.2)
            ax.set_xlabel('Production payoff evaluations N')
            if name=='accuracy':
                ax.set_ylabel('Point-reference RMSE (currency)')
                if ref.precision_radius is not None and np.isfinite(ref.precision_radius) and ref.precision_radius>0:
                    ax.axhline(ref.precision_radius,color='#222',linestyle='--',linewidth=1,label='reference radius')
                finite_values=group.rmse.to_numpy(dtype=float)
                has_positive=np.any(np.isfinite(finite_values)&(finite_values>0))
                positive_radius=ref.precision_radius is not None and np.isfinite(ref.precision_radius) and ref.precision_radius>0
                if has_positive or positive_radius:ax.set_yscale('log')
                else:ax.set_ylim(0,1)
                if not np.any(np.isfinite(finite_values)):
                    ax.text(.5,.5,'Reference unavailable\nRMSE withheld',ha='center',transform=ax.transAxes)
                elif not has_positive:
                    ax.text(.5,.5,'Observed point errors are zero\nSee zero-SE diagnostics',ha='center',transform=ax.transAxes)
            else:
                ax.axhline(.95,color='#222',linestyle='--',linewidth=1);ax.set_ylim(-.03,1.04)
                ax.set_ylabel('Fraction of reported intervals')
            ax.grid(alpha=.18)
        for ax in list(axes.flat)[len(contracts):]:ax.set_visible(False)
        handles,labels=axes.flat[0].get_legend_handles_labels()
        if handles:fig.legend(handles,labels,loc='upper center',ncol=min(6,len(labels)),bbox_to_anchor=(.5,.94),frameon=False)
        fig.suptitle('Asian pricing: accuracy against declared references' if name=='accuracy' else 'Interval calibration against a reference band',fontsize=16,y=.99)
        note=('Shading: percentile bootstrap across macro repeats. Dashed black: empirical reference radius; not a rigorous bound.' if name=='accuracy' else
              'Solid: possible coverage; dotted: definite coverage. Their gap reflects reference uncertainty; black: 95% nominal level.')
        fig.text(.5,.02,note,ha='center',fontsize=9)
        fig.tight_layout(rect=(0,.05,1,.88));fig.savefig(out/f'{name}.png',dpi=170,bbox_inches="tight");plt.close(fig)
    fig,axes=plt.subplots(1,2,figsize=(12,4.8))
    if len(bench):
        good=bench[bench.status=='completed']
        for method,group in good.groupby('method',sort=False):
            g=group.groupby('batch_size').elapsed_seconds
            med=g.median();lo=g.quantile(.25);hi=g.quantile(.75)
            axes[0].errorbar(med.index,med,yerr=[med-lo,hi-med],marker='o',capsize=3,label=method,color=COLORS[method])
        for method,g in allocations[allocations.status=='completed'].groupby('method',sort=False):
            axes[1].plot(g.batch_size,g.peak_traced_bytes/2**20,marker='o',label=method,color=COLORS[method])
        for ax in axes:ax.set_xscale('log',base=2);ax.set_yscale('log');ax.set_xlabel('Batch size');ax.grid(alpha=.18)
        axes[0].set_ylabel('Median complete-estimator seconds (IQR)');axes[1].set_ylabel('Peak traced allocation (MiB; not RSS)')
        handles,labels=axes[0].get_legend_handles_labels()
        if handles:axes[0].legend(handles,labels,frameon=False,fontsize=9)
        for ax,valid,message in [(axes[0],len(good),'All benchmark repetitions failed'),
                                 (axes[1],int((allocations.status=='completed').sum()),'All allocation passes failed')]:
            if not valid:
                ax.set_axis_off();ax.text(.5,.5,message+'\nSee retained failure rows',ha='center',va='center',transform=ax.transAxes)
    else:
        for ax in axes:ax.set_axis_off();ax.text(.5,.5,'Benchmark disabled\nNo timing or allocation claims',ha='center',va='center',transform=ax.transAxes)
    fig.suptitle('Measured computation: timing and separate allocation pass',fontsize=15)
    fig.text(.5,.02,'Timing includes RNG, transforms, payoffs and uncertainty. Sobol allocates a full scramble; allocations are a separate untimed pass.',ha='center',fontsize=9)
    fig.tight_layout(rect=(0,.06,1,.94));fig.savefig(out/'efficiency.png',dpi=170,bbox_inches="tight");plt.close(fig)
    fig,ax=plt.subplots(figsize=(max(12,len(contracts)*1.4),4.8))
    for i,ref in enumerate(contracts):
        radius=ref.precision_radius
        if radius is not None and np.isfinite(radius) and radius>0:
            ax.scatter(i,math.log10(radius),s=75,color='#d55e00' if ref.status=='low_precision' else '#009e73')
            ax.annotate(f'{radius:.2g}',(i,math.log10(radius)),xytext=(0,8),textcoords='offset points',ha='center',fontsize=8)
        elif radius==0:
            ax.scatter(i,-16,color='#009e73');ax.annotate('analytic: 0',(i,-16),xytext=(0,6),textcoords='offset points',ha='center',fontsize=8)
        else:ax.text(i,1,'unavailable',ha='center',rotation=90,transform=ax.get_xaxis_transform())
    ax.axhline(math.log10(.0005),color='#222',linestyle='--',label='study precision target: 0.0005')
    ax.set_xticks(range(len(contracts)),[f'{r.fixing_count} fixings\nK={r.strike:g}' for r in contracts])
    ax.set_ylabel('log10(declared reference radius / currency unit)');ax.set_title('Reference precision is part of the result',fontsize=15)
    ax.legend(frameon=False);ax.grid(axis='y',alpha=.18)
    fig.text(.5,.02,'Orange: low precision; green: available. Cross-method radii and quadrature diagnostics are empirical, not guaranteed bounds.',ha='center',fontsize=9)
    fig.tight_layout(rect=(0,.05,1,1));fig.savefig(out/'reference_precision.png',dpi=170,bbox_inches="tight");plt.close(fig)
