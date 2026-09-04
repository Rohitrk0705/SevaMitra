"use client";

import React, { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import {
  Mic,
  MicOff,
  Send,
  Shield,
  ArrowLeft,
  CheckCircle2,
  Volume2,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";

const SAMPLE_PROMPTS = {
  rekha:
    "I am Rekha Murugan, 18 years old from Coimbatore, Tamil Nadu. I just cleared my 12th standard and joined an engineering college. My father is a small farmer. Are there government scholarships or fee assistance schemes I can apply for?",
  rajesh:
    "I am Rajesh Kumar, 45 years old from Thanjavur, Tamil Nadu. I cultivate 2 acres of paddy. I want to apply for agricultural input subsidies and PM-KISAN benefits.",
};

export default function DelegatePage() {
  const router = useRouter();
  const [persona, setPersona] = useState<"rekha" | "rajesh">("rekha");
  const [inputText, setInputText] = useState(SAMPLE_PROMPTS.rekha);
  const [isRecording, setIsRecording] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const toggleRecording = () => {
    if (!isRecording) {
      setIsRecording(true);
      // Simulate speech recognition transcription
      setTimeout(() => {
        setIsRecording(false);
      }, 3500);
    } else {
      setIsRecording(false);
    }
  };

  const handlePersonaChange = (p: "rekha" | "rajesh") => {
    setPersona(p);
    setInputText(SAMPLE_PROMPTS[p]);
  };

  const handleDelegate = async () => {
    setIsSubmitting(true);
    try {
      await fetch("/api/delegate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          persona,
          message: inputText,
          voice: isRecording,
        }),
      });
    } catch (err) {
      console.warn("Delegate POST simulated fallback:", err);
    }

    // Redirect to main page with stream auto-started
    router.push(`/?persona=${persona}&stream=true`);
  };

  return (
    <div className="min-h-screen flex flex-col bg-[#05080a] text-slate-100 antialiased font-sans">
      {/* Top Navbar */}
      <header className="border-b border-slate-800 bg-slate-950/80 backdrop-blur-md px-4 sm:px-8 py-3.5 flex items-center justify-between">
        <Link
          href="/"
          className="flex items-center gap-2 text-xs text-slate-400 hover:text-slate-200 transition-colors"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to Live Agent Stream
        </Link>
        <div className="flex items-center gap-2">
          <Shield className="h-4 w-4 text-emerald-400" />
          <span className="text-sm font-semibold tracking-tight text-white">
            SevaMithra Delegate Intake
          </span>
        </div>
      </header>

      {/* Main Intake Screen */}
      <main className="flex-1 flex flex-col items-center justify-center p-4 sm:p-6 max-w-3xl mx-auto w-full space-y-8 my-6">
        {/* Header Hero */}
        <div className="text-center space-y-3">
          <Badge
            variant="agent"
            className="px-3 py-1 text-xs tracking-wider uppercase font-mono"
          >
            Autonomous Citizen Delegation
          </Badge>
          <h1 className="text-3xl sm:text-4xl font-extrabold tracking-tight bg-gradient-to-r from-white via-slate-100 to-slate-400 bg-clip-text text-transparent">
            Speak or describe your situation.
          </h1>
          <p className="text-sm text-slate-400 max-w-lg mx-auto">
            Authorize SevaMithra&apos;s autonomous multi-agent swarm to discover eligible welfare schemes, verify credentials via DigiLocker, file applications, and pursue statutory RTI escalations on your behalf.
          </p>
        </div>

        {/* Persona quick switch */}
        <div className="flex items-center justify-center gap-2 bg-slate-900/90 border border-slate-800 p-1.5 rounded-xl">
          <button
            type="button"
            onClick={() => handlePersonaChange("rekha")}
            className={`text-xs px-4 py-2 rounded-lg font-medium transition-all ${
              persona === "rekha"
                ? "bg-emerald-600 text-white shadow-md shadow-emerald-950"
                : "text-slate-400 hover:text-slate-200"
            }`}
          >
            🎓 Rekha Murugan (Student, 18)
          </button>
          <button
            type="button"
            onClick={() => handlePersonaChange("rajesh")}
            className={`text-xs px-4 py-2 rounded-lg font-medium transition-all ${
              persona === "rajesh"
                ? "bg-emerald-600 text-white shadow-md shadow-emerald-950"
                : "text-slate-400 hover:text-slate-200"
            }`}
          >
            🌾 Rajesh Kumar (Farmer, 45)
          </button>
        </div>

        {/* Big Centered Mic Button with Pulse */}
        <div className="flex flex-col items-center space-y-3">
          <button
            type="button"
            onClick={toggleRecording}
            className={`relative group h-28 w-28 sm:h-32 sm:w-32 rounded-full flex items-center justify-center transition-all duration-300 ${
              isRecording
                ? "bg-rose-600 shadow-[0_0_50px_rgba(225,29,72,0.6)] scale-105"
                : "bg-gradient-to-br from-emerald-500 to-teal-700 hover:from-emerald-400 hover:to-teal-600 shadow-[0_0_35px_rgba(16,185,129,0.3)] hover:scale-105 active:scale-95"
            }`}
          >
            {isRecording ? (
              <MicOff className="h-12 w-12 text-white animate-pulse" />
            ) : (
              <Mic className="h-12 w-12 text-white" />
            )}

            {/* Ripple rings when recording */}
            {isRecording && (
              <>
                <span className="absolute inset-0 rounded-full border-2 border-rose-400 animate-ping opacity-75"></span>
                <span className="absolute -inset-3 rounded-full border border-rose-500/50 animate-pulse"></span>
              </>
            )}
          </button>

          <span className="text-xs font-mono text-slate-400 flex items-center gap-1.5">
            {isRecording ? (
              <span className="text-rose-400 font-semibold flex items-center gap-1">
                <Volume2 className="h-3.5 w-3.5 animate-bounce" />
                Listening & transcribing Tamil / English speech...
              </span>
            ) : (
              "Click to speak in your local language"
            )}
          </span>
        </div>

        {/* Textarea Fallback Card */}
        <div className="w-full bg-slate-900/70 border border-slate-800 rounded-xl p-5 shadow-xl space-y-3">
          <div className="flex items-center justify-between text-xs text-slate-400">
            <label htmlFor="situation-text" className="font-semibold text-slate-300">
              Or type your background and requirement:
            </label>
            <span className="font-mono text-[11px] text-slate-500">
              English / தமிழ் / Hindi
            </span>
          </div>

          <textarea
            id="situation-text"
            rows={4}
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
            placeholder="E.g., I am a farmer in Thanjavur needing input subsidies, or a student looking for higher education grant..."
            className="w-full bg-slate-950 border border-slate-700 rounded-lg p-3.5 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-emerald-500/80 font-sans leading-relaxed resize-none"
          />

          <div className="flex flex-wrap items-center justify-between gap-3 pt-2">
            <div className="text-[11px] text-slate-400 flex items-center gap-1">
              <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400" />
              Direct autonomous execution with e-Sign & DigiLocker
            </div>

            <Button
              type="button"
              size="lg"
              disabled={isSubmitting || !inputText.trim()}
              onClick={handleDelegate}
              className="bg-emerald-600 hover:bg-emerald-500 text-white text-sm font-semibold gap-2 shadow-lg shadow-emerald-950 px-6 py-2.5"
            >
              {isSubmitting ? (
                "Dispatching Agents..."
              ) : (
                <>
                  <Send className="h-4 w-4" />
                  Delegate to SevaMithra
                </>
              )}
            </Button>
          </div>
        </div>
      </main>
    </div>
  );
}
