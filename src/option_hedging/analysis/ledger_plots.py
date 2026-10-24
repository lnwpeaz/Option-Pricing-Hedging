"""Inspect individual cash/trade records; not an ensemble performance chart."""

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np


def make_ledger_figure(hedged, unhedged, *, strike):
    rows = hedged.ledger
    times = [r.time for r in rows]
    with plt.rc_context({'font.family':'DejaVu Sans', 'font.size':10,
                         'axes.spines.top':False, 'axes.spines.right':False,
                         'figure.facecolor':'#f8fafc', 'axes.facecolor':'white'}):
        fig,axes = plt.subplots(2,2,figsize=(12,8),layout='constrained')
        axes[0,0].plot(times,[r.spot for r in rows],'-o',color='#008b8b',label='Explicit illustrative stock path')
        axes[0,0].axhline(strike,ls='--',color='#64748b',label='Strike')
        axes[0,0].set(title='Observed prices at decision dates',ylabel='Stock price')
        axes[0,0].legend(fontsize=8)
        axes[0,1].step(times,[r.stock_after for r in rows],where='post',color='#008b8b',label='Shares after event')
        axes[0,1].scatter(times,[r.stock_after for r in rows],color='#008b8b',s=25)
        axes[0,1].set(title='Shares held; expiry closes to zero',ylabel='Shares for one short call',ylim=(-.03,1.03))
        axes[1,0].plot(times,[r.cash_after for r in rows],'-o',color='#008b8b',label='Hedged cash')
        axes[1,0].plot(times,[r.cash_after for r in unhedged.ledger],'--o',color='#64748b',label='Unhedged cash')
        axes[1,0].set(title='Cash after events; final point is settled P&L',ylabel='Cash balance')
        axes[1,0].legend(fontsize=8)
        axes[1,1].step(times,np.cumsum([r.transaction_cost for r in rows]),where='post',color='#dd7935')
        axes[1,1].scatter(times,np.cumsum([r.transaction_cost for r in rows]),color='#dd7935',s=25)
        axes[1,1].set(title='Nominal stock-trading costs, including close',ylabel='Cumulative costs paid')
        for ax in axes.flat:
            ax.set_xlabel('Time (years)')
            ax.grid(alpha=.15)
        fig.suptitle('SELF-FINANCING HEDGE LEDGER  |  One path, every cash flow visible\n'
                     'Before expiry cash/assets exclude the short-call liability; this is no performance ranking',
                     fontsize=13,fontweight='bold')
    return fig
