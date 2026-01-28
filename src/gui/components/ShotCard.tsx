
import React, { useState, useEffect } from 'react';
import {
  Sparkles,
  Video,
  RotateCw,
  Info,
  Play,
  ChevronDown,
  ChevronUp,
  Image as ImageIcon,
  Loader2,
  Lock,
  Terminal,
  X,
  Code2
} from 'lucide-react';
import { Shot, Asset } from '../types';
import { api } from '../lib/api';

interface ShotCardProps {
  shot: Shot;
  index: number;
  onUpdate: (shot: Shot) => void;
}

export const ShotCard: React.FC<ShotCardProps> = ({ shot, index, onUpdate }) => {
  const [expanded, setExpanded] = useState(false);
  const [isGenerating, setIsGenerating] = useState<'images' | 'video' | null>(null);
  const [showPromptsModal, setShowPromptsModal] = useState(false);
  const [activeView, setActiveView] = useState<'video' | 'keyframes'>('video');

  const hasImages = shot.assets.some(a => a.type === 'IMAGE_START') && shot.assets.some(a => a.type === 'IMAGE_END');
  const hasVideo = shot.assets.some(a => a.type === 'CLIP');

  const startImage = shot.assets.find(a => a.role === 'start_ref');
  const endImage = shot.assets.find(a => a.role === 'end_ref');
  const clip = shot.assets.find(a => a.type === 'CLIP');

  // Auto-switch to video view if video is available
  useEffect(() => {
    if (hasVideo) {
      setActiveView('video');
    } else if (hasImages) {
      setActiveView('keyframes');
    }
  }, [hasVideo, hasImages]);

  const handleGenerateImages = async (e?: React.MouseEvent) => {
    e?.stopPropagation();
    setIsGenerating('images');

    try {
      // Call the backend API to generate images
      await api.generateImages(shot.shot_id.split('_')[0], shot.shot_id, 1, shot.video_id);

      // Reload the shot data after a short delay to get the new assets
      setTimeout(() => {
        setIsGenerating(null);
      }, 2000);
    } catch (error) {
      console.error('Failed to generate images:', error);
      setIsGenerating(null);
    }
  };

  // Handle Escape key for modal
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && showPromptsModal) {
        setShowPromptsModal(false);
      }
    };

    if (showPromptsModal) {
      document.addEventListener('keydown', handleKeyDown);
    }
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [showPromptsModal]);

  const handleGenerateVideo = async (e?: React.MouseEvent) => {
    e?.stopPropagation();
    if (!hasImages) return;
    setIsGenerating('video');

    try {
      // Call the backend API to generate video
      await api.generateClip(shot.shot_id.split('_')[0], shot.shot_id, 1, shot.video_id);

      // Start polling for video completion
      const pollInterval = 3000; // Poll every 3 seconds
      const maxAttempts = 60; // Maximum 3 minutes (60 * 3s = 180s)
      let attempts = 0;

      const pollForVideo = async () => {
        try {
          attempts++;

          // Fetch the latest shot data
          const updatedShot = await api.getShot(shot.shot_id.split('_')[0], shot.shot_id, 1);

          // Check if video is now available
          const videoReady = updatedShot.assets.some(a => a.type === 'CLIP');

          if (videoReady) {
            // Video is ready! Update the UI
            console.log('✅ Video generation complete!');
            setIsGenerating(null);
            setActiveView('video');
            onUpdate(updatedShot); // Notify parent to update the shot data
            return;
          }

          // Continue polling if not ready and haven't exceeded max attempts
          if (attempts < maxAttempts) {
            setTimeout(pollForVideo, pollInterval);
          } else {
            console.warn('⏱️ Polling timeout - video may still be generating');
            setIsGenerating(null);
          }
        } catch (error) {
          console.error('Error polling for video:', error);
          // Continue polling even on error, as it might be a temporary network issue
          if (attempts < maxAttempts) {
            setTimeout(pollForVideo, pollInterval);
          } else {
            setIsGenerating(null);
          }
        }
      };

      // Start polling after initial delay
      setTimeout(pollForVideo, pollInterval);

    } catch (error) {
      console.error('Failed to generate video:', error);
      setIsGenerating(null);
    }
  };

  return (
    <div className={`relative group transition-all duration-300 ${expanded ? 'z-10 py-2' : 'z-0'}`}>
      {/* Prompts Modal Overlay */}
      {showPromptsModal && (
        <div
          className="fixed inset-0 z-[100] flex items-center justify-center p-6 bg-black/90 backdrop-blur-sm animate-in fade-in duration-200"
          role="dialog"
          aria-modal="true"
          aria-labelledby={`modal-title-${shot.shot_id}`}
        >
          <div className="bg-black border border-green-900/50 w-full max-w-2xl rounded-sm shadow-[0_0_50px_rgba(20,83,45,0.2)] overflow-hidden flex flex-col max-h-[80vh] animate-in zoom-in-95 duration-200 font-mono">
            <header className="p-4 border-b border-green-900/50 flex items-center justify-between shrink-0 bg-green-950/10">
              <div className="flex items-center gap-3">
                <Terminal size={18} className="text-green-500" />
                <h3 id={`modal-title-${shot.shot_id}`} className="text-sm font-bold text-green-500 uppercase tracking-widest">
                  SYS.PROMPTS // {shot.shot_id}
                </h3>
              </div>
              <button
                onClick={() => setShowPromptsModal(false)}
                className="p-1.5 text-green-700 hover:text-green-400 hover:bg-green-900/20 rounded transition-all"
                aria-label="Close Modal"
              >
                <X size={20} />
              </button>
            </header>
            <div className="p-6 overflow-y-auto space-y-6 bg-black">
              <div className="space-y-2">
                <div className="flex items-center gap-2 text-[10px] font-bold text-green-600 uppercase tracking-tighter">
                  <span className="w-1.5 h-1.5 bg-green-600" /> &gt; INPUT_STREAM_A [START_REF]
                </div>
                <div className="p-4 bg-black border border-green-900/30 text-xs text-green-400 leading-relaxed shadow-inner">
                  <span className="opacity-50 mr-2 select-none">$</span>
                  {shot.prompts?.image_a || "ERR: NO_DATA_STREAM"}
                </div>
              </div>

              <div className="space-y-2">
                <div className="flex items-center gap-2 text-[10px] font-bold text-green-600 uppercase tracking-tighter">
                  <span className="w-1.5 h-1.5 bg-green-600" /> &gt; INPUT_STREAM_B [END_REF]
                </div>
                <div className="p-4 bg-black border border-green-900/30 text-xs text-green-400 leading-relaxed shadow-inner">
                  <span className="opacity-50 mr-2 select-none">$</span>
                  {shot.prompts?.image_b || "ERR: NO_DATA_STREAM"}
                </div>
              </div>

              {shot.prompts?.video && (
                <div className="space-y-2">
                  <div className="flex items-center gap-2 text-[10px] font-bold text-green-600 uppercase tracking-tighter">
                    <span className="w-1.5 h-1.5 bg-green-600" /> &gt; KINETIC_VECTOR_PLAN
                  </div>
                  <div className="p-4 bg-black border border-green-900/30 text-xs text-green-400 leading-relaxed shadow-inner">
                    <span className="opacity-50 mr-2 select-none">$</span>
                    {shot.prompts.video}
                  </div>
                </div>
              )}
            </div>
            <footer className="p-4 bg-green-950/10 border-t border-green-900/50 flex justify-end">
              <button
                onClick={() => setShowPromptsModal(false)}
                className="px-6 py-2 bg-green-900/20 hover:bg-green-900/40 text-green-500 border border-green-800 hover:border-green-500 rounded-none text-xs font-bold uppercase tracking-wider transition-all"
              >
                [ TERMINATE_VIEW ]
              </button>
            </footer>
          </div>
        </div>
      )}

      <div
        className={`bg-slate-900 border border-slate-800 rounded-xl overflow-hidden shadow-lg transition-all ${!expanded ? 'hover:border-slate-600 cursor-pointer hover:bg-slate-800/40' : 'shadow-2xl'}`}
        onClick={() => !expanded && setExpanded(true)}
      >
        {/* Header */}
        <header className={`px-4 flex items-center justify-between border-b border-slate-800/50 bg-slate-800/10 transition-all ${!expanded ? 'h-14' : 'h-16 bg-slate-800/30'}`}>
          <div className="flex items-center gap-4 flex-1">
            <div className="w-7 h-7 bg-slate-950 border border-slate-800 rounded flex items-center justify-center">
              <span className="mono text-[10px] font-bold text-slate-400">{String(index + 1).padStart(2, '0')}</span>
            </div>

            <div className="flex flex-col min-w-[120px]">
              <span className="text-[9px] mono font-bold text-slate-500 tracking-tighter uppercase">{shot.shot_id}</span>
              <h4 className="text-xs font-bold text-slate-200 uppercase tracking-wide truncate max-w-[150px]">Segment {index + 1}</h4>
            </div>

            <div className="h-6 w-px bg-slate-800" />

            <div className="flex items-center gap-2 overflow-hidden">
              {isGenerating ? (
                <div className="flex items-center gap-2 px-2 py-0.5 bg-slate-950 rounded border border-slate-800">
                  <Loader2 className="animate-spin text-indigo-500" size={10} />
                  <span className="text-[8px] mono font-bold text-slate-500 uppercase animate-pulse">Processing...</span>
                </div>
              ) : (
                <>
                  {hasImages && (
                    <div className="flex gap-0.5">
                      <img src={startImage?.url} className="w-12 h-7 object-cover rounded border border-slate-700" alt="S" />
                      <img src={endImage?.url} className="w-12 h-7 object-cover rounded border border-slate-700" alt="E" />
                    </div>
                  )}
                  {hasVideo && (
                    <div className="w-12 h-7 bg-indigo-900/40 rounded border border-indigo-500/50 overflow-hidden flex items-center justify-center">
                      <Play size={8} className="text-indigo-400 fill-indigo-400" />
                    </div>
                  )}
                  {!hasImages && !hasVideo && (
                    <div className="w-12 h-7 border border-dashed border-slate-800 rounded flex items-center justify-center text-slate-700">
                      <ImageIcon size={10} />
                    </div>
                  )}
                </>
              )}
            </div>

            <div className="hidden lg:flex items-center gap-4 ml-auto px-2">
              <div className="flex items-center gap-1.5">
                <span className="text-[9px] mono text-slate-500 font-bold uppercase">Time</span>
                <span className="text-[10px] font-bold text-indigo-400">{shot.duration_s}s</span>
              </div>
              <div className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-[8px] font-bold uppercase tracking-wider ${shot.status === 'DONE' ? 'text-emerald-500 border border-emerald-500/20 bg-emerald-500/5' : 'text-amber-500 border border-amber-500/20 bg-amber-500/5'
                }`}>
                {shot.status}
              </div>
            </div>
          </div>

          <div className="flex items-center gap-1.5 ml-4">
            {!expanded && !hasVideo && (
              <button
                onClick={(e) => hasImages ? handleGenerateVideo(e) : handleGenerateImages(e)}
                className={`hidden sm:flex items-center gap-1.5 px-2 py-1 rounded text-[9px] font-bold uppercase tracking-wider transition-all border ${hasImages
                  ? 'bg-blue-600/10 hover:bg-blue-600 text-blue-400 hover:text-white border-blue-500/30'
                  : 'bg-indigo-600/10 hover:bg-indigo-600 text-indigo-400 hover:text-white border-indigo-500/30'
                  }`}
              >
                {hasImages ? <Video size={10} /> : <Sparkles size={10} />}
                {hasImages ? 'Render Clip' : 'Forge Frames'}
              </button>
            )}
            <button
              onClick={(e) => { e.stopPropagation(); setExpanded(!expanded); }}
              className="p-1.5 text-slate-400 hover:text-white bg-slate-800/50 rounded transition-all"
            >
              {expanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
            </button>
          </div>
        </header>

        {expanded && (
          <div className="animate-in slide-in-from-top-2 duration-200">
            <div className="relative min-h-[250px] bg-slate-950 flex flex-col overflow-hidden">
              {isGenerating && (
                <div className="absolute inset-0 z-20 flex flex-col items-center justify-center bg-slate-950/90 backdrop-blur-md">
                  <Loader2 className="animate-spin text-indigo-500 mb-2" size={32} />
                  <p className="text-[10px] mono font-bold text-slate-200 animate-pulse tracking-widest uppercase">
                    {isGenerating === 'images' ? 'Generating Reference Frames...' : 'Synthesizing Kinetic Motion...'}
                  </p>
                </div>
              )}

              {/* View Toggle Tabs */}
              {hasVideo && hasImages && !isGenerating && (
                <div className="absolute top-4 left-1/2 -translate-x-1/2 z-20 flex items-center gap-1 bg-black/60 backdrop-blur-sm p-1 rounded-lg border border-white/10 shadow-2xl">
                  <button
                    onClick={() => setActiveView('video')}
                    className={`px-3 py-1.5 rounded-md text-[9px] font-bold uppercase transition-all flex items-center gap-2 ${activeView === 'video'
                      ? 'bg-indigo-600 text-white shadow-lg'
                      : 'text-slate-400 hover:text-white hover:bg-white/10'
                      }`}
                  >
                    <Play size={10} fill={activeView === 'video' ? "currentColor" : "none"} />
                    Motion
                  </button>
                  <button
                    onClick={() => setActiveView('keyframes')}
                    className={`px-3 py-1.5 rounded-md text-[9px] font-bold uppercase transition-all flex items-center gap-2 ${activeView === 'keyframes'
                      ? 'bg-blue-600 text-white shadow-lg'
                      : 'text-slate-400 hover:text-white hover:bg-white/10'
                      }`}
                  >
                    <ImageIcon size={10} />
                    Frames
                  </button>
                </div>
              )}

              {/* Main Content Area */}
              {hasVideo && activeView === 'video' && !isGenerating ? (
                <div className="aspect-video w-full relative bg-black group/player">
                  <video src={clip?.url} className="w-full h-full object-cover" autoPlay loop muted playsInline />
                  <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-transparent to-transparent opacity-0 group-hover/player:opacity-100 transition-opacity flex items-end justify-between p-4">
                    <span className="text-[9px] mono font-bold text-slate-400 uppercase tracking-widest">
                      Generated via <span className="text-white">Veo</span>
                    </span>
                    <button onClick={handleGenerateVideo} className="flex items-center gap-2 px-3 py-1.5 bg-white/10 hover:bg-white/20 text-white border border-white/20 hover:border-white/50 rounded text-[10px] font-bold uppercase transition-all backdrop-blur-md">
                      <RotateCw size={12} /> Re-roll Clip
                    </button>
                  </div>
                </div>
              ) : hasImages && (activeView === 'keyframes' || !hasVideo) && !isGenerating ? (
                <div className="flex h-full min-h-[250px] relative">
                  <div className="flex-1 border-r border-slate-900 overflow-hidden group/frame-a relative">
                    <img src={startImage?.url} className="w-full h-full object-cover opacity-80 transition-opacity group-hover/frame-a:opacity-100" alt="Start" />
                    <div className="absolute top-0 left-0 right-0 p-3 bg-gradient-to-b from-black/60 to-transparent">
                      <div className="flex items-center gap-2">
                        <span className="w-2 h-2 rounded-full bg-indigo-500 shadow-[0_0_10px_rgba(99,102,241,0.5)]"></span>
                        <span className="text-[9px] font-bold text-white uppercase tracking-wider text-shadow">Start Ref</span>
                      </div>
                    </div>
                  </div>
                  <div className="flex-1 overflow-hidden group/frame-b relative">
                    <img src={endImage?.url} className="w-full h-full object-cover opacity-80 transition-opacity group-hover/frame-b:opacity-100" alt="End" />
                    <div className="absolute top-0 left-0 right-0 p-3 bg-gradient-to-b from-black/60 to-transparent flex justify-end">
                      <div className="flex items-center gap-2">
                        <span className="text-[9px] font-bold text-white uppercase tracking-wider text-shadow">End Ref</span>
                        <span className="w-2 h-2 rounded-full bg-purple-500 shadow-[0_0_10px_rgba(168,85,247,0.5)]"></span>
                      </div>
                    </div>
                  </div>

                  {!hasVideo && (
                    <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
                      <div className="pointer-events-auto flex flex-col items-center gap-3">
                        <button onClick={handleGenerateVideo} className="flex items-center gap-3 px-8 py-4 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white rounded-2xl font-bold transition-all shadow-2xl scale-110 active:scale-95 group/btn">
                          <div className="p-1 bg-white/20 rounded-full group-hover/btn:rotate-90 transition-transform">
                            <Video size={16} fill="currentColor" />
                          </div>
                          Render Kinetic Sequence
                        </button>
                        <button onClick={handleGenerateImages} className="text-[10px] font-bold text-slate-400 hover:text-white transition-all uppercase mono bg-black/40 hover:bg-black/60 px-3 py-1.5 rounded-lg backdrop-blur-sm border border-white/10 hover:border-white/30 flex items-center gap-2">
                          <RotateCw size={10} /> Regenerate Keyframes
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              ) : (
                <div className="flex-1 flex flex-col items-center justify-center p-8 text-center bg-slate-900/20">
                  <div className="w-14 h-14 rounded-full bg-slate-950 border border-slate-800 flex items-center justify-center mb-6 group-hover:border-indigo-500 transition-all">
                    <Sparkles size={24} className="text-slate-600" />
                  </div>
                  <div className="mb-6">
                    <h5 className="text-sm font-bold text-slate-300 uppercase tracking-widest mb-1">Stage 3: Image Synthesis</h5>
                    <p className="text-[10px] text-slate-500 uppercase mono">Establishing anchors for motion</p>
                  </div>
                  <div className="flex items-center gap-3">
                    <button onClick={handleGenerateImages} className="flex items-center gap-2 px-6 py-3 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-[11px] font-bold uppercase tracking-wider transition-all shadow-lg">
                      <Sparkles size={14} /> Forge Keyframes
                    </button>
                    <div className="px-4 py-3 bg-slate-800/40 rounded-xl border border-slate-800 flex items-center gap-2 text-slate-600 cursor-not-allowed grayscale">
                      <Lock size={14} />
                      <span className="text-[10px] font-bold uppercase mono">Video Locked</span>
                    </div>
                  </div>
                </div>
              )}
            </div>

            <div className="p-4 grid grid-cols-1 md:grid-cols-2 gap-4 border-t border-slate-800 bg-slate-900/40">
              <div className="space-y-3">
                <div>
                  <div className="flex items-center justify-between mb-1">
                    <div className="flex items-center gap-2">
                      <Info size={12} className="text-indigo-400" />
                      <span className="text-[9px] font-bold uppercase tracking-widest text-slate-500 mono">Script Segment</span>
                    </div>
                    {/* Modal Trigger */}
                    <button
                      onClick={(e) => { e.stopPropagation(); setShowPromptsModal(true); }}
                      className="flex items-center gap-1 px-2 py-0.5 bg-slate-800 hover:bg-indigo-600 text-slate-400 hover:text-white rounded border border-slate-700 transition-all text-[8px] font-bold uppercase tracking-tight mono"
                    >
                      <Code2 size={10} /> View Prompts
                    </button>
                  </div>
                  <p className="text-xs text-slate-200 leading-relaxed font-medium italic">"{shot.script_text}"</p>
                </div>
                <div>
                  <div className="flex items-center gap-2 mb-1">
                    <Play size={12} className="text-purple-400" />
                    <span className="text-[9px] font-bold uppercase tracking-widest text-slate-500 mono">Visual Intent</span>
                  </div>
                  <p className="text-[10px] text-slate-400 leading-relaxed font-mono">{shot.intent}</p>
                </div>
              </div>

              <div className="bg-slate-950/40 rounded-xl p-3 border border-slate-800/50">
                <span className="text-[9px] font-bold uppercase tracking-widest text-indigo-400 mono block mb-2 underline decoration-indigo-500/30">AI Production Plan</span>
                <div className="space-y-2">
                  <div className="flex gap-2">
                    <div className="w-0.5 h-full bg-indigo-500/20 rounded-full" />
                    <p className="text-[10px] text-slate-400"><span className="text-slate-600 font-bold uppercase mr-1">METAPHOR:</span> {shot.ai_plan?.metaphor}</p>
                  </div>
                  <div className="flex gap-2">
                    <div className="w-0.5 h-full bg-purple-500/20 rounded-full" />
                    <p className="text-[10px] text-slate-400"><span className="text-slate-600 font-bold uppercase mr-1">CAMERA:</span> {shot.ai_plan?.camera}</p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
