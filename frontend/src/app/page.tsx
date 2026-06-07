"use client";

import { useState, useRef, useEffect } from "react";
import { Play, Terminal, Video, Loader2, Code2, Save } from "lucide-react";
import Editor from "@monaco-editor/react";

export default function Home() {
  const [prompt, setPrompt] = useState("");
  const [isCompiling, setIsCompiling] = useState(false);
  const [logs, setLogs] = useState<string[]>([]);
  const [videoUrl, setVideoUrl] = useState<string | null>(null);
  
  // Interactive Mode State
  const [activeTab, setActiveTab] = useState<"video" | "code">("video");
  const [generatedCode, setGeneratedCode] = useState("from manim import *\n\nclass GeneratedScene(Scene):\n    def construct(self):\n        pass");
  const [sceneName, setSceneName] = useState("GeneratedScene");

  const logsEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll logs
  useEffect(() => {
    logsEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [logs]);

  const handleGenerate = async () => {
    setIsCompiling(true);
    setLogs(["[INFO] Contacting AI Backend..."]);
    setVideoUrl(null);
    setActiveTab("video");

    try {
      const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8020";
      const response = await fetch(`${API_URL}/generate-render`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt }),
      });

      if (!response.body) throw new Error("No response body");

      const reader = response.body.getReader();
      const decoder = new TextDecoder("utf-8");
      
      let fullText = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value);
        fullText += chunk;

        // Extract Code blocks
        const codeMatches = [...fullText.matchAll(/\[CODE\]\n([\s\S]*?)\n\[\/CODE\]/g)];
        if (codeMatches.length > 0) {
          setGeneratedCode(codeMatches[codeMatches.length - 1][1]);
        }

        // Extract Scene Name
        const sceneMatch = fullText.match(/Generated scene class name: '(.*?)'/);
        if (sceneMatch) {
          setSceneName(sceneMatch[1]);
        }

        // Parse logs to screen (filtering out code block chunks)
        const lines = chunk.split("\n").filter(
          line => line.trim() !== "" && !line.startsWith("[CODE]") && !line.startsWith("[/CODE]") && !line.includes("from manim import")
        );
        
        if (lines.length > 0) {
            setLogs((prev) => [...prev, ...lines]);
        }

        for (const line of lines) {
          if (line.includes("[SUCCESS]")) {
            const urlMatch = line.match(/Video URL: (.*)/);
            if (urlMatch) {
              setVideoUrl(`${API_URL}${urlMatch[1]}?t=${Date.now()}`); // Add timestamp to bypass cache
            }
          }
        }
      }
    } catch (error) {
      setLogs((prev) => [...prev, `[ERROR] Connection failed: ${error}`]);
    } finally {
      setIsCompiling(false);
    }
  };

  const handleManualCompile = async () => {
    setIsCompiling(true);
    setLogs(["[INFO] Sending manual code to Docker compiler..."]);
    setVideoUrl(null);
    setActiveTab("video");

    try {
      const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8020";
      const response = await fetch(`${API_URL}/compile`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ code: generatedCode, scene_name: sceneName }),
      });

      if (!response.body) throw new Error("No response body");

      const reader = response.body.getReader();
      const decoder = new TextDecoder("utf-8");

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value);
        const lines = chunk.split("\n").filter(line => line.trim() !== "");
        setLogs((prev) => [...prev, ...lines]);

        for (const line of lines) {
          if (line.includes("[SUCCESS]")) {
            const urlMatch = line.match(/Video URL: (.*)/);
            if (urlMatch) {
              setVideoUrl(`${API_URL}${urlMatch[1]}?t=${Date.now()}`);
            }
          }
        }
      }
    } catch (error) {
      setLogs((prev) => [...prev, `[ERROR] Connection failed: ${error}`]);
    } finally {
      setIsCompiling(false);
    }
  };

  return (
    <main className="flex-1 flex flex-col md:flex-row p-4 md:p-8 gap-6 max-w-7xl mx-auto w-full h-screen">
      {/* LEFT COLUMN: Input Area */}
      <div className="flex-1 flex flex-col gap-4">
        <div className="flex flex-col gap-2">
          <h1 className="text-3xl font-bold tracking-tighter bg-clip-text text-transparent bg-gradient-to-r from-emerald-400 to-cyan-500">
            Prompt2Pixel
          </h1>
          <p className="text-zinc-400 text-sm">
            Describe what you want Manim to draw in natural language.
          </p>
        </div>

        {/* Preset Templates */}
        <div className="flex flex-wrap gap-2">
          {[
            { icon: "🔵", text: "Draw a glowing red square that morphs into a blue circle" },
            { icon: "📐", text: "Animate the Pythagorean theorem equation step by step" },
            { icon: "📈", text: "Plot a glowing sine wave on a 2D axis" }
          ].map((preset, idx) => (
            <button
              key={idx}
              onClick={() => setPrompt(preset.text)}
              className="px-3 py-1.5 rounded-full bg-zinc-800/50 border border-zinc-700 hover:border-cyan-500/50 hover:bg-zinc-800 text-xs text-zinc-300 transition-colors flex items-center gap-1.5"
            >
              <span>{preset.icon}</span>
              <span className="truncate max-w-[150px] sm:max-w-xs">{preset.text}</span>
            </button>
          ))}
        </div>

        <div className="relative flex-1 min-h-[150px]">
          <textarea
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            placeholder="e.g., Draw a glowing red square that slowly morphs into a blue circle while rotating 90 degrees..."
            className="w-full h-full p-4 rounded-xl bg-zinc-900/50 border border-zinc-800 focus:border-cyan-500/50 focus:ring-1 focus:ring-cyan-500/50 transition-all outline-none resize-none font-sans text-sm text-zinc-300 placeholder:text-zinc-600"
          />
        </div>

        <button
          onClick={handleGenerate}
          disabled={isCompiling || !prompt.trim()}
          className="flex items-center justify-center gap-2 w-full py-4 rounded-xl bg-gradient-to-r from-emerald-500 to-cyan-500 text-black font-bold hover:brightness-110 transition-all disabled:opacity-50 disabled:cursor-not-allowed group shadow-lg shadow-cyan-500/20"
        >
          {isCompiling ? (
            <Loader2 className="w-5 h-5 animate-spin" />
          ) : (
            <Play className="w-5 h-5 group-hover:scale-110 transition-transform" />
          )}
          {isCompiling ? "Generating & Compiling..." : "Generate AI Render"}
        </button>
        
        {/* Manual Compile Option */}
        <div className="mt-4 pt-4 border-t border-zinc-800 flex flex-col gap-2">
          <p className="text-xs text-zinc-500 uppercase font-bold tracking-wider">Manual Override</p>
          <div className="flex gap-2">
            <input 
              type="text" 
              value={sceneName} 
              onChange={(e) => setSceneName(e.target.value)}
              className="flex-1 bg-zinc-900 border border-zinc-800 rounded-lg px-3 py-2 text-sm text-zinc-300 font-mono outline-none focus:border-cyan-500"
              placeholder="Scene Class Name"
            />
            <button
              onClick={handleManualCompile}
              disabled={isCompiling || !generatedCode.trim()}
              className="flex items-center justify-center gap-2 px-4 py-2 rounded-lg bg-zinc-800 text-white text-sm font-semibold hover:bg-zinc-700 transition-colors disabled:opacity-50"
            >
              <Save className="w-4 h-4" />
              Recompile Code
            </button>
          </div>
        </div>
      </div>

      {/* RIGHT COLUMN: Output Area */}
      <div className="flex-[1.5] flex flex-col gap-6">
        
        {/* Output Tabs */}
        <div className="flex items-center gap-1 border-b border-zinc-800 pb-2">
          <button 
            onClick={() => setActiveTab("video")}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-semibold transition-colors ${activeTab === "video" ? "bg-zinc-800 text-white" : "text-zinc-500 hover:text-zinc-300"}`}
          >
            <Video className="w-4 h-4" /> Video Render
          </button>
          <button 
            onClick={() => setActiveTab("code")}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-semibold transition-colors ${activeTab === "code" ? "bg-zinc-800 text-white" : "text-zinc-500 hover:text-zinc-300"}`}
          >
            <Code2 className="w-4 h-4" /> Python Source
          </button>
        </div>

        {/* Tab Content: Video or Editor */}
        <div className="flex-1 rounded-xl border border-zinc-800 overflow-hidden relative min-h-[350px] bg-black">
          {activeTab === "video" ? (
             <div className="w-full h-full flex items-center justify-center">
              {videoUrl ? (
                <video src={videoUrl} controls autoPlay className="w-full h-full object-contain" />
              ) : (
                <div className="text-zinc-600 flex flex-col items-center gap-2">
                  <Video className="w-8 h-8 opacity-20" />
                  <span className="text-sm">No video rendered yet</span>
                </div>
              )}
            </div>
          ) : (
            <div className="w-full h-full p-1">
              <Editor
                height="100%"
                defaultLanguage="python"
                theme="vs-dark"
                value={generatedCode}
                onChange={(val) => setGeneratedCode(val || "")}
                options={{
                  minimap: { enabled: false },
                  fontSize: 14,
                  fontFamily: 'var(--font-geist-mono)',
                  padding: { top: 16 }
                }}
              />
            </div>
          )}
        </div>

        {/* Bottom: Terminal Logs */}
        <div className="flex flex-col gap-2 h-[250px]">
          <div className="flex items-center gap-2 text-zinc-400">
            <Terminal className="w-4 h-4" />
            <span className="text-xs font-semibold uppercase tracking-wider">Compiler Console</span>
          </div>
          <div className="flex-1 rounded-xl bg-black border border-zinc-800 p-4 overflow-y-auto font-mono text-xs shadow-inner">
            {logs.length === 0 ? (
              <span className="text-zinc-700">Waiting for instructions...</span>
            ) : (
              <div className="flex flex-col gap-1">
                {logs.map((log, index) => {
                  let textColor = "text-zinc-400";
                  if (log.includes("[ERROR]")) textColor = "text-red-400";
                  if (log.includes("[SUCCESS]")) textColor = "text-emerald-400";
                  if (log.includes("[HEALING]")) textColor = "text-amber-400";
                  if (log.includes("[INFO]")) textColor = "text-cyan-400";
                  return (
                    <span key={index} className={`${textColor} break-all`}>
                      {log}
                    </span>
                  );
                })}
                <div ref={logsEndRef} />
              </div>
            )}
          </div>
        </div>
      </div>
    </main>
  );
}
