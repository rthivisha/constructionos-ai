"use client";
import { motion } from "motion/react";
import { useEffect, useRef } from "react";
import { cn } from "@/app/lib/utils";
interface Beam {
  x: number; y: number; width: number; length: number; angle: number;
  speed: number; opacity: number; hue: number; pulse: number; pulseSpeed: number;
}
function createBeam(width: number, height: number): Beam {
  return {
    x: Math.random() * width * 1.5 - width * 0.25,
    y: Math.random() * height * 1.5 - height * 0.25,
    width: 30 + Math.random() * 60,
    length: height * 2.5,
    angle: -35 + Math.random() * 10,
    speed: 0.6 + Math.random() * 1.2,
    opacity: 0.12 + Math.random() * 0.16,
    hue: 190 + Math.random() * 70,
    pulse: Math.random() * Math.PI * 2,
    pulseSpeed: 0.02 + Math.random() * 0.03,
  };
}
export default function BeamsBackground({ className, intensity = "strong", children }: { className?: string; children?: React.ReactNode; intensity?: "subtle"|"medium"|"strong"; }) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const beamsRef = useRef<Beam[]>([]);
  const animRef = useRef<number>(0);
  const opacityMap = { subtle: 0.7, medium: 0.85, strong: 1 };
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    const resize = () => {
      const dpr = window.devicePixelRatio || 1;
      canvas.width = window.innerWidth * dpr;
      canvas.height = window.innerHeight * dpr;
      canvas.style.width = window.innerWidth + "px";
      canvas.style.height = window.innerHeight + "px";
      ctx.scale(dpr, dpr);
      beamsRef.current = Array.from({ length: 30 }, () => createBeam(canvas.width, canvas.height));
    };
    resize();
    window.addEventListener("resize", resize);
    function draw(beam: Beam) {
      ctx!.save();
      ctx!.translate(beam.x, beam.y);
      ctx!.rotate((beam.angle * Math.PI) / 180);
      const op = beam.opacity * (0.8 + Math.sin(beam.pulse) * 0.2) * opacityMap[intensity];
      const g = ctx!.createLinearGradient(0, 0, 0, beam.length);
      g.addColorStop(0, `hsla(${beam.hue},85%,65%,0)`);
      g.addColorStop(0.4, `hsla(${beam.hue},85%,65%,${op})`);
      g.addColorStop(0.6, `hsla(${beam.hue},85%,65%,${op})`);
      g.addColorStop(1, `hsla(${beam.hue},85%,65%,0)`);
      ctx!.fillStyle = g;
      ctx!.fillRect(-beam.width / 2, 0, beam.width, beam.length);
      ctx!.restore();
    }
    function animate() {
      ctx!.clearRect(0, 0, canvas!.width, canvas!.height);
      ctx!.filter = "blur(35px)";
      beamsRef.current.forEach((beam, i) => {
        beam.y -= beam.speed; beam.pulse += beam.pulseSpeed;
        if (beam.y + beam.length < -100) { beamsRef.current[i] = createBeam(canvas!.width, canvas!.height); }
        draw(beam);
      });
      animRef.current = requestAnimationFrame(animate);
    }
    animate();
    return () => { window.removeEventListener("resize", resize); cancelAnimationFrame(animRef.current); };
  }, [intensity]);
  return (
    <div className={cn("relative min-h-screen w-full overflow-hidden bg-neutral-950", className)}>
      <canvas ref={canvasRef} className="absolute inset-0 pointer-events-none" style={{ filter: "blur(15px)" }} />
      <motion.div animate={{ opacity: [0.05, 0.15, 0.05] }} className="absolute inset-0 pointer-events-none" transition={{ duration: 10, ease: "easeInOut", repeat: Infinity }} />
      <div className="relative z-10 w-full">{children}</div>
    </div>
  );
}
