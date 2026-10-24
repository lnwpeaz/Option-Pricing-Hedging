"""Paired short-call replication-error figures, not long-portfolio return charts."""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np


def make_figures(cases,metrics,*,reference_volatility,costs,frequencies):
    lookup={(r['scenario_id'],r['premium_basis']):r for r in metrics}
    ref=[c for c in cases if c['hedge_volatility']==reference_volatility]
    hedge=[c for c in ref if c['strategy']=='delta_hedged']
    unhedged=next(c for c in ref if c['strategy']=='unhedged')
    colors=('#008b8b','#dd7935','#64748b','#7c5cab')
    figures={}
    with plt.rc_context({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,
                         'axes.spines.right':False,'figure.facecolor':'#f8fafc','axes.facecolor':'white'}):
        fig,axes=plt.subplots(2,2,figsize=(13,9),layout='constrained')
        all_ref=[unhedged]+sorted(hedge,key=lambda c:(c['one_way_cost_bps'],c['rebalance_every_steps']))
        for i,c in enumerate(all_ref):
            m=lookup[c['scenario_id'],'model']
            color='#64748b' if c['strategy']=='unhedged' else colors[frequencies.index(c['rebalance_every_steps'])%len(colors)]
            axes[0,0].vlines(i,m['rmse_ci_low'],m['rmse_ci_high'],color=color,lw=2)
            axes[0,0].scatter(i,m['rmse'],color=color,s=35)
        labels=['unhedged' if c['strategy']=='unhedged' else f"{c['rebalance_every_steps']}step\n{c['one_way_cost_bps']:g}bps" for c in all_ref]
        axes[0,0].set_xticks(range(len(labels)),labels)
        if all(lookup[c['scenario_id'],'model']['rmse_ci_low']>0 for c in all_ref):
            axes[0,0].set_yscale('log')
        axes[0,0].set(title='Replication RMSE with pointwise bootstrap95% intervals',ylabel='RMSE (premium units)')
        zero=[c for c in hedge if c['one_way_cost_bps']==0]
        for i,c in enumerate([unhedged]+zero):
            data=np.sort(c['terminal_pnl'])
            label='unhedged' if c['strategy']=='unhedged' else f"every{c['rebalance_every_steps']} steps, no costs"
            axes[0,1].plot(data,np.arange(1,len(data)+1)/len(data),color=colors[(i+2)%len(colors)],label=label)
        axes[0,1].set(title='Full empirical distributions; all paths retained',xlabel='Signed short-call hedger P&L',ylabel='Empirical cumulative probability')
        axes[0,1].legend(fontsize=8)
        for i,freq in enumerate(frequencies):
            rows=[lookup[c['scenario_id'],'model'] for c in sorted(hedge,key=lambda c:c['one_way_cost_bps']) if c['rebalance_every_steps']==freq]
            x=[m['mean_financed_costs'] for m in rows]
            axes[1,0].plot(x,[m['rmse'] for m in rows],'-o',color=colors[i%len(colors)],label=f'every{freq} steps')
            for xx,m in zip(x,rows):
                axes[1,0].vlines(xx,m['rmse_ci_low'],m['rmse_ci_high'],color=colors[i%len(colors)])
                axes[1,0].annotate(f"{m['one_way_cost_bps']:g}bps",(xx,m['rmse']),xytext=(4,5),textcoords='offset points',fontsize=8)
        axes[1,0].set(title='Trading cost versus replication accuracy',xlabel='Mean terminal value of trading costs',ylabel='RMSE')
        axes[1,0].legend(fontsize=8)
        selected=next(c for c in hedge if c['rebalance_every_steps']==frequencies[0] and c['one_way_cost_bps']==costs[len(costs)//2])
        funding=np.sort(selected['max_cash_borrowing'])
        axes[1,1].plot(funding,np.arange(1,len(funding)+1)/len(funding),color='#008b8b')
        axes[1,1].set(title=f"Peak cash borrowing: every{frequencies[0]} steps / {selected['one_way_cost_bps']:g}bps",
                       xlabel='Model-premium cash borrowing; NOT broker margin',ylabel='Empirical cumulative probability')
        fig.suptitle('PAIRED MONTE CARLO HEDGE STUDY  |  Reference-sigma short-call replication\n'
                     'These are model-conditioned errors and funding diagnostics, not returns of a long stock/ETF portfolio',fontsize=13,fontweight='bold')
        figures['risk_and_cost.png']=fig
        fig,axes=plt.subplots(2,2,figsize=(12,8.5),layout='constrained')
        middle=costs[len(costs)//2]
        for col,basis in enumerate(('model','common_reference')):
            for i,freq in enumerate(frequencies):
                selected=sorted([c for c in cases if c['strategy']=='delta_hedged' and c['rebalance_every_steps']==freq and c['one_way_cost_bps']==middle],key=lambda c:c['hedge_volatility'])
                rows=[lookup[c['scenario_id'],basis] for c in selected]
                x=[c['hedge_volatility']*100 for c in selected]
                for ax,field in zip(axes[:,col],('mean_pnl','rmse')):
                    ax.plot(x,[m[field] for m in rows],'-o',color=colors[i%len(colors)],label=f'every{freq} steps')
                    for xx,m in zip(x,rows):
                        ax.vlines(xx,m[field+'_ci_low'],m[field+'_ci_high'],color=colors[i%len(colors)])
                    ax.axvline(reference_volatility*100,color='#64748b',ls='--',alpha=.5)
                    ax.set_xlabel('Hedge/model volatility (%)')
            axes[0,col].set_title('Own model premium' if basis=='model' else 'Same reference premium: isolate policy effects')
            axes[0,col].set_ylabel('Mean hedger P&L')
            axes[1,col].set_ylabel('Replication RMSE')
            axes[0,col].legend(fontsize=8)
        fig.suptitle(f'VOLATILITY MISSPECIFICATION  |  Trading cost{middle:g}bps\n'
                     'Changing sigma changes premium AND hedge decisions; two premium bases prevent confounding',fontsize=13,fontweight='bold')
        figures['volatility_and_premium.png']=fig
        for fig in figures.values():
            for ax in fig.axes:
                ax.grid(alpha=.15)
    return figures
