
import React, { useState, useEffect } from 'react';
import {
  Play,
  ChevronDown,
  Plus,
  Terminal,
  Cpu,
  Zap,
  Sparkles,
  Search,
  ArrowRight,
  CheckCircle2
} from 'lucide-react';
import { ShotCard } from './ShotCard';
import { Shot } from '../types';
import { api } from '../lib/api';

interface ShotEditorProps {
  runId: string;
  runName: string;
}

type PipelineStage = 'PLANNING' | 'PROMPTING' | 'READY';

export const ShotEditor: React.FC<ShotEditorProps> = ({ runId, runName }) => {
  const [shots, setShots] = useState<Shot[]>([]);
  const [stage, setStage] = useState<PipelineStage>('PLANNING');
  const [planningLogs, setPlanningLogs] = useState<string[]>([]);
  const [isPlanningComplete, setIsPlanningComplete] = useState(false);
  const [promptProgress, setPromptProgress] = useState(0);
  const [videoId, setVideoId] = useState<string>('VID_001');


  useEffect(() => {
    // Check if run has existing shots - if so, skip to READY
    loadExistingRunData();
  }, [runId]);

  const transformBackendShots = (backendShots: any[]): Shot[] => {
    return backendShots.map(shot => {
      // Parse camera_config if it's a string
      let camera = shot.camera_config;
      if (typeof shot.camera_config === 'string') {
        try {
          camera = JSON.parse(shot.camera_config);
        } catch (e) {
          camera = shot.camera_config;
        }
      }

      // Transform assets to match GUI format
      const assets = shot.assets
        .filter((asset: any) => asset.type !== 'PROMPT') // Exclude PROMPT assets from the assets array
        .map((asset: any) => ({
          type: asset.type as 'IMAGE_START' | 'IMAGE_END' | 'CLIP',
          asset_id: asset.asset_id,
          url: asset.url || `/api/assets/${asset.asset_id}/file`,
          role: asset.role as 'start_ref' | 'end_ref' | 'final_clip'
        }));

      // Find prompts in assets - they're stored as type PROMPT with roles start_ref/end_ref
      const promptAssets = shot.assets.filter((a: any) => a.type === 'PROMPT');
      let prompts = undefined;

      if (promptAssets.length > 0) {
        try {
          // Find start and end prompts
          const startPromptAsset = promptAssets.find((a: any) => a.role === 'start_ref');
          const endPromptAsset = promptAssets.find((a: any) => a.role === 'end_ref');

          let image_a = '';
          let image_b = '';

          if (startPromptAsset && startPromptAsset.metadata) {
            const startMeta = JSON.parse(startPromptAsset.metadata);
            image_a = startMeta.prompt || '';
          }

          if (endPromptAsset && endPromptAsset.metadata) {
            const endMeta = JSON.parse(endPromptAsset.metadata);
            image_b = endMeta.prompt || '';
          }

          // Extract video prompt from shot metadata (metaphor + camera)
          let video = '';
          if (shot.metaphor && camera) {
            const cameraStr = typeof camera === 'string' ? camera : (camera.movement || 'static');
            video = `${shot.metaphor}, ${cameraStr} movement`;
          }

          if (image_a || image_b || video) {
            prompts = {
              image_a,
              image_b,
              video
            };
          }
        } catch (e) {
          console.error('Failed to parse prompts metadata:', e);
        }
      }

      return {
        shot_id: shot.shot_id,
        video_id: shot.video_id,
        script_text: shot.script_text || '',
        intent: shot.intent || '',
        duration_s: shot.duration_s || 0,
        status: shot.status,
        assets,
        ai_plan: {
          metaphor: shot.metaphor || '',
          camera: typeof camera === 'string' ? camera : JSON.stringify(camera)
        },
        prompts
      };
    });
  };



  const loadExistingRunData = async () => {
    try {
      // 1. Get Status first
      const status = await api.getRunStatus(runId);

      // 2. Get Shots
      try {
        const backendShots = await api.getShots(runId);
        if (backendShots && backendShots.length > 0) {
          setShots(transformBackendShots(backendShots));
          if (backendShots[0].video_id) {
            setVideoId(backendShots[0].video_id);
          }
        }
      } catch (e) {
        console.warn("No shots found yet.");
      }

      // 3. Determine Stage based on Backend Status
      // status IS the status object from getRunStatus
      const backStage = (status?.current_stage || 'planning').toLowerCase();
      const backStatus = (status?.stage_status || 'running').toLowerCase();

      console.log(`Synced State: Stage=${backStage}, Status=${backStatus}`);

      if (backStage === 'planning') {
        if (backStatus === 'done') {
          setIsPlanningComplete(true);
          setStage('PLANNING'); // Show "Confirm" button
        } else {
          startPlanningStage(); // Resume polling
        }
      }
      else if (backStage === 'prompts') {
        if (backStatus === 'done') {
          setStage('READY'); // Prompts done, ready for review
        } else {
          setStage('PROMPTING');
          startPromptingStage(); // Resume polling
        }
      }
      else {
        // images or clips -> READY
        setStage('READY');
      }

    } catch (error) {
      console.error('Failed to load existing run data:', error);
      startPlanningStage();
    }
  };

  const startPlanningStage = () => {
    setStage('PLANNING');
    setIsPlanningComplete(false);
    setPlanningLogs(["Initializing Mission Planner..."]);

    const pollInterval = setInterval(async () => {
      try {
        const status = await api.getRunStatus(runId);

        if (status) {
          if (status.progress_message) {
            setPlanningLogs(prev => {
              const lastLog = prev[prev.length - 1];
              if (lastLog !== status.progress_message) {
                return [...prev.slice(-9), status.progress_message];
              }
              return prev;
            });
          }

          if (status.stage_status === 'done') {
            clearInterval(pollInterval);
            setIsPlanningComplete(true);
            setPlanningLogs(prev => [...prev, "Mission Planning Compete."]);
            // Refresh shots
            loadShots();
          }
        }
      } catch (error) {
        console.error("Error polling planning status:", error);
      }
    }, 2000);

    return () => clearInterval(pollInterval);
  };

  const handleProceedToPrompting = async () => {
    try {
      setStage('PROMPTING');
      // Execute real backend stage
      await api.executeStage(runId, 'prompts', videoId);
      startPromptingStage();
    } catch (e) {
      console.error("Failed to start prompting:", e);
      alert("Failed to start prompting stage. Check console.");
    }
  };

  const startPromptingStage = async () => {
    setPromptProgress(0);

    const pollInterval = setInterval(async () => {
      try {
        const status = await api.getRunStatus(runId);

        if (status) {
          // Map backend progress (if available) or fake it gently if running
          // Backend might not send detailed progress mainly just 'done'
          if (status.stage_status === 'done') {
            clearInterval(pollInterval);
            setPromptProgress(100);
            setTimeout(async () => {
              await loadShots();
              setStage('READY');
            }, 500);
          } else {
            // Fake progress for liveliness if backend log indicates work
            setPromptProgress(prev => Math.min(prev + 1, 90));
          }
        }
      } catch (e) {
        console.error("Error polling prompting:", e);
      }
    }, 2000); // 2s poll
  };

  const loadShots = async () => {
    try {
      const backendShots = await api.getShots(runId);
      const transformedShots = transformBackendShots(backendShots);
      setShots(transformedShots);
    } catch (error) {
      console.error('Failed to load shots:', error);
      // Don't clear shots on error, keep existing
    }
  };

  const getMockShots = (id: string): Shot[] => [
    {
      shot_id: `${id}_s001`,
      video_id: 'vid_001',
      script_text: "In the heart of the neon city, shadows dance across the chrome facades.",
      intent: "Establishing shot of a futuristic metropolis at night. Heavy rain, high contrast neon lighting.",
      duration_s: 3.5,
      status: 'DONE',
      assets: [
        { type: 'IMAGE_START', asset_id: 'a001', url: 'https://picsum.photos/id/10/800/450', role: 'start_ref' },
        { type: 'IMAGE_END', asset_id: 'a002', url: 'https://picsum.photos/id/11/800/450', role: 'end_ref' },
        { type: 'CLIP', asset_id: 'a003', url: 'https://storage.googleapis.com/gtv-videos-bucket/sample/ForBiggerBlazes.mp4', role: 'final_clip' }
      ],
      ai_plan: {
        metaphor: "A weeping city made of light and silicon.",
        camera: "Slow drone push-in from wide to medium wide."
      },
      prompts: {
        image_a: "Hyper-realistic wide shot of a cyberpunk city at night, heavy rain, glowing neon signs in electric blue and pink, wet asphalt reflecting lights, 8k, cinematic lighting.",
        image_b: "Low angle medium shot focusing on the chrome facade of a skyscraper, shadows of flying vehicles passing over, rain droplets on metal, high-tech noir aesthetic.",
        video: "Smooth kinetic interpolation between frame A and frame B, rain falling in slow motion, flickering neon lights, slight camera vibration mimicking a drone."
      }
    },
    {
      shot_id: `${id}_s002`,
      video_id: 'vid_002',
      script_text: "A lone traveler waits for the late-night maglev, eyes reflecting the digital hum.",
      intent: "Close-up of a character's eyes. Subtle movement of holographic displays in the background.",
      duration_s: 2.8,
      status: 'PLANNED',
      assets: [
        { type: 'IMAGE_START', asset_id: 'a004', url: 'https://picsum.photos/id/20/800/450', role: 'start_ref' },
        { type: 'IMAGE_END', asset_id: 'a005', url: 'https://picsum.photos/id/21/800/450', role: 'end_ref' }
      ],
      ai_plan: {
        metaphor: "Reflection of a world they no longer recognize.",
        camera: "Static shot with shallow depth of field."
      },
      prompts: {
        image_a: "Extreme close up of a human eye, intricate iris details, vivid reflections of a holographic train schedule, futuristic station atmosphere, cinematic macro photography.",
        image_b: "Medium close up profile of a traveler wearing a tech-collar, looking at a departing blue light streak, digital bokeh background, moody lighting.",
        video: "Subtle micro-movement in the eye, iris contraction, holographic displays flickering and scrolling in the reflection, slow focal shift."
      }
    },
    {
      shot_id: `${id}_s003`,
      video_id: 'vid_003',
      script_text: "Suddenly, the power grid flickers. The neon pulse falters for a heartbeat.",
      intent: "Fast montage of flickering lights. Visual chaos, sudden blackout transitions.",
      duration_s: 4.2,
      status: 'PLANNED',
      assets: [],
      ai_plan: {
        metaphor: "A heart skipping a beat.",
        camera: "Quick shaky cam movements."
      },
      prompts: {
        image_a: "High contrast shot of a power substation with buzzing electricity, arcs of light, sparks flying, industrial cyberpunk setting.",
        image_b: "Total blackout shot of the city, only emergency red lights visible in the distance, smoke rising, eerie quiet atmosphere.",
        video: "Rapid staccato flickering between bright electrical arcs and pitch black, fast shutter speed, jittery camera motion, glitch effects."
      }
    }
  ];

  const handleUpdateShot = (updatedShot: Shot) => {
    setShots(prev => prev.map(s => s.shot_id === updatedShot.shot_id ? updatedShot : s));
  };

  return (
    <div className="flex flex-col h-full bg-slate-950">
      <header className="sticky top-0 z-30 bg-slate-950/80 backdrop-blur-xl border-b border-slate-800 p-4 md:px-8 flex items-center justify-between">
        <div className="flex items-center gap-6">
          <div>
            <div className="flex items-center gap-2 mb-0.5">
              <span className="text-[10px] mono font-bold text-slate-500 bg-slate-900 px-1.5 py-0.5 rounded border border-slate-800">{runId}</span>
              <span className="text-[10px] font-bold text-emerald-400 uppercase tracking-widest bg-emerald-500/10 px-1.5 py-0.5 rounded">LIVE PROD</span>
            </div>
            <h2 className="text-xl font-black text-white flex items-center gap-2">
              {runName}
              <ChevronDown size={18} className="text-slate-600" />
            </h2>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-500 text-white px-4 py-2 rounded-lg font-bold transition-all shadow-lg shadow-indigo-600/20 text-xs">
            <Play size={16} fill="currentColor" /> Preview Final
          </button>
        </div>
      </header>

      <div className="flex-1 overflow-y-auto">
        {stage === 'PLANNING' && (
          <div className="h-full flex flex-col items-center justify-center p-12 text-center animate-in fade-in zoom-in duration-300">
            <div className="relative mb-8">
              <div className={`w-20 h-20 rounded-full border-4 border-slate-800 transition-colors duration-500 ${isPlanningComplete ? 'border-emerald-500/50' : 'border-t-indigo-500 animate-spin'}`} />
              {isPlanningComplete ? (
                <CheckCircle2 className="absolute inset-0 m-auto text-emerald-400 animate-in zoom-in duration-300" size={32} />
              ) : (
                <Cpu className="absolute inset-0 m-auto text-indigo-400 animate-pulse" size={32} />
              )}
            </div>
            <h3 className="text-xl font-bold text-white mb-2 uppercase tracking-widest mono">Stage 1: Planning Mission</h3>
            <div className="max-w-md w-full bg-slate-900/50 border border-slate-800 rounded-xl p-4 text-left font-mono text-[10px] space-y-1 h-40 overflow-hidden relative mb-8">
              <div className="flex items-center gap-2 text-indigo-400 mb-2">
                <Terminal size={12} />
                <span>mission_planner_v2.log</span>
              </div>
              {planningLogs.map((log, i) => (
                <div key={i} className="text-slate-400 opacity-80 animate-in slide-in-from-bottom-1 fade-in">
                  <span className="text-slate-600">[{new Date().toLocaleTimeString()}]</span> {log}
                </div>
              ))}
              {!isPlanningComplete && <div className="animate-pulse text-indigo-500">_</div>}
              {isPlanningComplete && <div className="text-emerald-500 font-bold mt-2 uppercase">Planning Phase Completed. Awaiting Operator Approval.</div>}
            </div>

            {isPlanningComplete && (
              <div className="animate-in slide-in-from-top-4 duration-500 flex flex-col items-center gap-4">
                <button
                  onClick={handleProceedToPrompting}
                  className="flex items-center gap-3 px-8 py-4 bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 text-white rounded-2xl font-bold transition-all shadow-2xl shadow-indigo-600/20 group active:scale-95"
                >
                  Confirm & Generate Prompts <ArrowRight size={18} className="group-hover:translate-x-1 transition-transform" />
                </button>
                <p className="text-[10px] text-slate-500 uppercase tracking-widest mono">Manual Verification Required</p>
              </div>
            )}
          </div>
        )}

        {stage === 'PROMPTING' && (
          <div className="h-full flex flex-col items-center justify-center p-12 text-center animate-in fade-in slide-in-from-bottom-4 duration-300">
            <div className="w-20 h-20 bg-purple-500/10 rounded-3xl flex items-center justify-center text-purple-400 border border-purple-500/20 mb-8 animate-pulse shadow-2xl shadow-purple-500/10">
              <Sparkles size={40} />
            </div>
            <h3 className="text-xl font-bold text-white mb-1 uppercase tracking-widest mono">Stage 2: Prompt Engineering</h3>
            <p className="text-[10px] text-slate-500 uppercase tracking-widest mono mb-8">Generating Semantic Directives for Synthesis</p>

            <div className="max-w-md w-full">
              <div className="flex justify-between text-[10px] font-bold text-slate-500 uppercase mono mb-2">
                <span>Synthesizing Shot Descriptions</span>
                <span>{promptProgress}%</span>
              </div>
              <div className="w-full h-1.5 bg-slate-900 border border-slate-800 rounded-full overflow-hidden">
                <div
                  className="h-full bg-gradient-to-r from-purple-600 to-indigo-600 transition-all duration-300 ease-out shadow-[0_0_10px_rgba(168,85,247,0.5)]"
                  style={{ width: `${promptProgress}%` }}
                />
              </div>
              <div className="mt-8 flex items-center justify-center gap-6">
                <div className="flex flex-col items-center gap-1">
                  <div className="w-2 h-2 rounded-full bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.5)]" />
                  <span className="text-[8px] mono text-slate-500 font-bold uppercase">Image Gen A</span>
                </div>
                <div className="flex flex-col items-center gap-1">
                  <div className={`w-2 h-2 rounded-full ${promptProgress > 50 ? 'bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.5)]' : 'bg-slate-800'}`} />
                  <span className="text-[8px] mono text-slate-500 font-bold uppercase">Image Gen B</span>
                </div>
                <div className="flex flex-col items-center gap-1">
                  <div className={`w-2 h-2 rounded-full ${promptProgress > 90 ? 'bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.5)]' : 'bg-slate-800'}`} />
                  <span className="text-[8px] mono text-slate-500 font-bold uppercase">Kinetic Plan</span>
                </div>
              </div>
            </div>
          </div>
        )}

        {stage === 'READY' && (
          /* 
            CRITICAL: OPERATOR CONFIRMATION BLOCKING LOGIC
            This block renders the shot list ONLY when stage is 'READY'.
            The 'READY' stage is exclusively reached after the Operator manually confirms
            the plan in the 'PLANNING' stage (triggering 'PROMPTING' -> 'READY').
            This ensures no shots are visible or editable until explicit approval.
          */
          <div className="p-4 md:p-6 animate-in fade-in duration-500">
            <div className="max-w-4xl mx-auto space-y-2 pb-24 relative">
              <div className="absolute left-6 top-0 bottom-0 w-px bg-slate-800 -z-10" />
              {shots.map((shot, index) => (
                <ShotCard
                  key={shot.shot_id}
                  shot={shot}
                  index={index}
                  onUpdate={handleUpdateShot}
                />
              ))}
              <div className="flex justify-start pl-3 pt-4">
                <button className="group flex items-center gap-3 px-6 py-3 bg-slate-900 border border-slate-800 rounded-xl text-slate-400 hover:border-indigo-500/50 hover:text-indigo-400 transition-all shadow-xl">
                  <Plus size={18} className="group-hover:scale-110 transition-transform" />
                  <span className="text-xs font-bold tracking-tight uppercase mono">Add Shot Marker</span>
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
