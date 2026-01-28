
import React from 'react';
import { Clapperboard, Clock, Video, Plus, Search, Filter, MoreVertical } from 'lucide-react';
import { Run } from '../types';

interface DashboardProps {
  runs: Run[];
  onSelectRun: (id: string) => void;
  onNewRun: () => void;
}

export const Dashboard: React.FC<DashboardProps> = ({ runs, onSelectRun, onNewRun }) => {
  return (
    <div className="p-10 max-w-7xl mx-auto">
      <header className="flex items-center justify-between mb-12">
        <div>
          <h2 className="text-4xl font-extrabold tracking-tight text-white mb-2 italic">Hangar Dashboard</h2>
          <p className="text-slate-400 text-lg">Orchestrate your cinematic AI pipeline from here.</p>
        </div>
        <button 
          onClick={onNewRun}
          className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-500 text-white px-6 py-3 rounded-xl font-bold transition-all shadow-lg shadow-indigo-600/20"
        >
          <Plus size={20} />
          Initiate New Run
        </button>
      </header>

      {/* Stats row */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-12">
        {[
          { label: 'Active Productions', value: '12', icon: Video, color: 'text-emerald-400' },
          { label: 'Total Render Time', value: '142h', icon: Clock, color: 'text-amber-400' },
          { label: 'Assets Generated', value: '2.4k', icon: Clapperboard, color: 'text-indigo-400' },
        ].map((stat, i) => (
          <div key={i} className="bg-slate-900 border border-slate-800 p-6 rounded-2xl shadow-xl">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-slate-500 text-sm font-bold uppercase tracking-wider mb-1 mono">{stat.label}</p>
                <p className="text-3xl font-extrabold text-white tracking-tight">{stat.value}</p>
              </div>
              <stat.icon className={`${stat.color} opacity-80`} size={32} />
            </div>
          </div>
        ))}
      </div>

      {/* Runs Table Header */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl shadow-xl overflow-hidden">
        <div className="p-6 border-b border-slate-800 flex items-center justify-between">
          <div className="flex items-center gap-4 bg-slate-950 px-4 py-2 rounded-lg border border-slate-800 w-96">
            <Search size={18} className="text-slate-500" />
            <input type="text" placeholder="Search mission IDs..." className="bg-transparent border-none outline-none text-sm w-full text-slate-300" />
          </div>
          <div className="flex items-center gap-3">
            <button className="flex items-center gap-2 px-3 py-2 rounded-lg text-slate-400 hover:bg-slate-800 transition-all text-sm font-medium">
              <Filter size={16} /> Filter
            </button>
          </div>
        </div>
        
        <table className="w-full text-left">
          <thead className="bg-slate-900 text-slate-500 text-[11px] font-bold uppercase tracking-widest mono border-b border-slate-800">
            <tr>
              <th className="px-6 py-4">Run Detail</th>
              <th className="px-6 py-4">Status</th>
              <th className="px-6 py-4">Model Pipeline</th>
              <th className="px-6 py-4">Frames</th>
              <th className="px-6 py-4 text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/50">
            {runs.map((run) => (
              <tr 
                key={run.id} 
                className="hover:bg-slate-800/30 transition-all cursor-pointer group"
                onClick={() => onSelectRun(run.id)}
              >
                <td className="px-6 py-5">
                  <div className="flex items-center gap-4">
                    <div className="w-10 h-10 bg-slate-800 rounded-lg flex items-center justify-center text-slate-500 group-hover:bg-indigo-900/40 group-hover:text-indigo-400 transition-all">
                      <Clapperboard size={20} />
                    </div>
                    <div>
                      <div className="text-white font-bold mb-0.5">{run.name}</div>
                      <div className="text-[10px] mono text-slate-500 font-medium tracking-tighter uppercase">{run.id} • {new Date(run.createdAt).toLocaleDateString()}</div>
                    </div>
                  </div>
                </td>
                <td className="px-6 py-5">
                  <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[10px] font-bold uppercase tracking-wider ${
                    run.status === 'active' ? 'bg-emerald-500/10 text-emerald-500 border border-emerald-500/20' : 
                    run.status === 'completed' ? 'bg-indigo-500/10 text-indigo-400 border border-indigo-500/20' : 
                    'bg-slate-500/10 text-slate-500 border border-slate-500/20'
                  }`}>
                    <span className={`w-1.5 h-1.5 rounded-full ${run.status === 'active' ? 'bg-emerald-500 animate-pulse' : 'bg-current'}`} />
                    {run.status}
                  </span>
                </td>
                <td className="px-6 py-5">
                  <div className="text-xs font-semibold text-slate-300">{run.model}</div>
                  <div className="text-[10px] text-slate-500 mono">{run.visualStyle}</div>
                </td>
                <td className="px-6 py-5">
                  <div className="text-xs font-bold text-slate-300">{run.shotsCount} shots</div>
                  <div className="text-[10px] text-slate-500 mono">{(run.shotsCount * 12).toLocaleString()} assets</div>
                </td>
                <td className="px-6 py-5 text-right">
                  <button className="p-2 text-slate-500 hover:text-white transition-all">
                    <MoreVertical size={18} />
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        
        {runs.length === 0 && (
          <div className="py-20 text-center">
            <p className="text-slate-500 mb-4">No active runs found in your hangar.</p>
            <button onClick={onNewRun} className="text-indigo-400 hover:text-indigo-300 font-bold underline">Start your first mission</button>
          </div>
        )}
      </div>
    </div>
  );
};
