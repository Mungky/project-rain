"use client";

import { useEffect, useRef } from "react";

const LAYERS = [
  { count: 100, speedScale: 1.2, opacity: 0.3, width: 1.2, glow: true },
  { count: 40, speedScale: 1.8, opacity: 0.15, width: 1.5, glow: false },
  { count: 20, speedScale: 2.5, opacity: 0.08, width: 3, glow: false },
];

const TARGET_FPS = 45;
const FRAME_INTERVAL = 1000 / TARGET_FPS;

interface Particle {
  x: number;
  y: number;
  speed: number;
  length: number;
  layerIndex: number;
}

export function RainBackdrop() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const particlesRef = useRef<Particle[]>([]);
  const rafRef = useRef<number>(0);
  const lastFrameRef = useRef<number>(0);

  useEffect(() => {
    const prefersReduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (prefersReduced) return;

    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext("2d", { alpha: true });
    if (!ctx) return;

    function resize() {
      if (!canvas) return;
      canvas.width = window.innerWidth;
      canvas.height = window.innerHeight;
      initParticles();
    }

    function initParticles() {
      if (!canvas) return;
      const particles: Particle[] = [];
      LAYERS.forEach((layer, layerIndex) => {
        for (let i = 0; i < layer.count; i++) {
          particles.push({
            x: Math.random() * canvas.width,
            y: Math.random() * canvas.height,
            speed: (40 + Math.random() * 40) * layer.speedScale,
            length: (20 + Math.random() * 30) * layer.speedScale,
            layerIndex,
          });
        }
      });
      particlesRef.current = particles;
    }

    function draw(timestamp: number) {
      if (!canvas || !ctx) return;

      if (document.visibilityState !== "visible") {
        rafRef.current = requestAnimationFrame(draw);
        return;
      }

      const delta = timestamp - lastFrameRef.current;
      if (delta < FRAME_INTERVAL) {
        rafRef.current = requestAnimationFrame(draw);
        return;
      }
      const deltaTime = delta / 1000;
      lastFrameRef.current = timestamp;

      ctx.clearRect(0, 0, canvas.width, canvas.height);

      ctx.lineCap = "round";
      particlesRef.current.forEach((p) => {
        const layer = LAYERS[p.layerIndex];
        if (!layer) return;
        
        ctx.beginPath();
        if (layer.glow) {
          ctx.shadowBlur = 3;
          ctx.shadowColor = "rgba(255, 255, 255, 0.3)";
        } else {
          ctx.shadowBlur = 0;
        }
        
        ctx.strokeStyle = `rgba(255, 255, 255, ${layer.opacity})`;
        ctx.lineWidth = layer.width;
        ctx.moveTo(p.x, p.y);
        ctx.lineTo(p.x, p.y + p.length);
        ctx.stroke();

        p.y += p.speed * deltaTime * 60;
        if (p.y > canvas.height) {
          p.y = -p.length;
          p.x = Math.random() * canvas.width;
        }
      });

      rafRef.current = requestAnimationFrame(draw);
    }

    resize();
    window.addEventListener("resize", resize, { passive: true });
    rafRef.current = requestAnimationFrame(draw);

    return () => {
      window.removeEventListener("resize", resize);
      cancelAnimationFrame(rafRef.current);
    };
  }, []);

  return (
    <div className="fixed inset-0 z-0 bg-black overflow-hidden">
      {/* Monochrome Noir Cinematic Background (Black & White Scale Only) */}
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top,rgba(40,40,40,0.5)_0%,rgba(0,0,0,1)_85%)]" />
      <div className="absolute inset-0 bg-gradient-to-b from-transparent via-transparent to-black" />
      
      {/* Canvas for Rain - Sharp white particles */}
      <canvas
        ref={canvasRef}
        className="absolute inset-0 pointer-events-none brightness-125"
        aria-hidden="true"
      />

      {/* Atmospheric Mist Layer */}
      <div className="absolute inset-0 backdrop-blur-[10px] opacity-20 pointer-events-none" />
      
      {/* High-Contrast Vignette */}
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,transparent_20%,rgba(0,0,0,0.85)_100%)] pointer-events-none" />
      
      {/* Cinematic Grain */}
      <div className="absolute inset-0 opacity-[0.04] pointer-events-none bg-[url('https://grainy-gradients.vercel.app/noise.svg')]" />
    </div>
  );
}