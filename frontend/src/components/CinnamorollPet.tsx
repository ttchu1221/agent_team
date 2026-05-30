"use client";

import { useEffect, useRef, useState, useCallback } from "react";

// ============================================================
//  玉桂狗 (Cinnamoroll) 虚拟宠物组件
//  准确外观：黑色眼睛、长垂耳、粉色腮红、白色蓬松
// ============================================================

type PetState = "idle" | "wander" | "sleep" | "happy" | "follow" | "play";
type Direction = "left" | "right";

interface PetPosition {
  x: number;
  y: number;
}

const STATE_DURATIONS: Record<PetState, [number, number]> = {
  idle: [3000, 6000],
  wander: [4000, 8000],
  sleep: [8000, 15000],
  happy: [2000, 3000],
  follow: [5000, 10000],
  play: [3000, 5000],
};

const THOUGHTS: Record<PetState, string[]> = {
  idle: ["☕", "💭", "✨", "🎵", "💫"],
  wander: ["🚶", "🌈", "🔍", "🌸", "🍃"],
  sleep: ["💤", "😴", "🌙", "☁️", "🫧"],
  happy: ["💖", "🎉", "⭐", "🥰", "✨"],
  follow: ["👀", "🏃", "💕", "🌟", "🎯"],
  play: ["🎮", "🎈", "🎪", "🎠", "🎡"],
};

export default function CinnamorollPet() {
  const [pos, setPos] = useState<PetPosition>({ x: 0, y: 0 });
  const [state, setState] = useState<PetState>("idle");
  const [direction, setDirection] = useState<Direction>("right");
  const [thought, setThought] = useState<string>("");
  const [showThought, setShowThought] = useState(false);
  const [isBlinking, setIsBlinking] = useState(false);
  const [tailWag, setTailWag] = useState(false);
  const [earFlap, setEarFlap] = useState(false);
  const [hearts, setHearts] = useState<{ id: number; x: number; y: number }[]>([]);
  const [zCount, setZCount] = useState(0);
  const [isDragging, setIsDragging] = useState(false);
  const [initialized, setInitialized] = useState(false);

  const posRef = useRef<PetPosition>({ x: 0, y: 0 });
  const stateRef = useRef<PetState>("idle");
  const mouseRef = useRef<PetPosition>({ x: 0, y: 0 });
  const timerRef = useRef<ReturnType<typeof setTimeout>>();
  const blinkTimerRef = useRef<ReturnType<typeof setInterval>>();
  const zTimerRef = useRef<ReturnType<typeof setInterval>>();
  const heartIdRef = useRef(0);
  const dragOffset = useRef<PetPosition>({ x: 0, y: 0 });

  useEffect(() => {
    if (typeof window === "undefined") return;
    const x = window.innerWidth - 120;
    const y = window.innerHeight - 160;
    posRef.current = { x, y };
    setPos({ x, y });
    setInitialized(true);
  }, []);

  useEffect(() => {
    const handleMouse = (e: MouseEvent) => {
      mouseRef.current = { x: e.clientX, y: e.clientY };
    };
    window.addEventListener("mousemove", handleMouse);
    return () => window.removeEventListener("mousemove", handleMouse);
  }, []);

  useEffect(() => {
    const blink = () => {
      setIsBlinking(true);
      setTimeout(() => setIsBlinking(false), 150);
    };
    blinkTimerRef.current = setInterval(() => {
      if (stateRef.current !== "sleep" && Math.random() > 0.5) blink();
    }, 2500);
    return () => clearInterval(blinkTimerRef.current);
  }, []);

  const scheduleNextState = useCallback(() => {
    clearTimeout(timerRef.current);
    const currentState = stateRef.current;
    const [min, max] = STATE_DURATIONS[currentState];
    const duration = min + Math.random() * (max - min);

    timerRef.current = setTimeout(() => {
      const distToMouse = Math.hypot(
        mouseRef.current.x - posRef.current.x,
        mouseRef.current.y - posRef.current.y
      );

      let nextState: PetState;
      if (distToMouse < 200 && Math.random() < 0.35) {
        nextState = "follow";
      } else {
        const pool: PetState[] = ["idle", "wander", "idle", "wander", "sleep", "play"];
        if (distToMouse < 350) pool.push("follow");
        nextState = pool[Math.floor(Math.random() * pool.length)];
      }

      setState(nextState);
      stateRef.current = nextState;

      const thoughts = THOUGHTS[nextState];
      setThought(thoughts[Math.floor(Math.random() * thoughts.length)]);
      setShowThought(true);
      setTimeout(() => setShowThought(false), 2000);

      if (nextState === "sleep") {
        setZCount(0);
        zTimerRef.current = setInterval(() => {
          setZCount((c) => (c >= 3 ? 0 : c + 1));
        }, 1200);
      } else {
        clearInterval(zTimerRef.current);
        setZCount(0);
      }

      scheduleNextState();
    }, duration);
  }, []);

  useEffect(() => {
    if (!initialized) return;
    scheduleNextState();
    return () => clearTimeout(timerRef.current);
  }, [initialized, scheduleNextState]);

  useEffect(() => {
    if (!initialized || isDragging) return;

    let raf: number;
    const speed = 1.2;

    const tick = () => {
      const s = stateRef.current;
      const p = { ...posRef.current };
      let moved = false;

      if (s === "wander") {
        const angle = Math.random() * Math.PI * 2;
        p.x += Math.cos(angle) * speed * 2;
        p.y += Math.sin(angle) * speed * 2;
        moved = true;
      } else if (s === "follow") {
        const dx = mouseRef.current.x - p.x;
        const dy = mouseRef.current.y - p.y;
        const dist = Math.hypot(dx, dy);
        if (dist > 60) {
          p.x += (dx / dist) * speed * 1.5;
          p.y += (dy / dist) * speed * 1.5;
          moved = true;
        }
      } else if (s === "idle") {
        p.y += Math.sin(Date.now() / 800) * 0.3;
        moved = true;
      }

      p.x = Math.max(20, Math.min(window.innerWidth - 80, p.x));
      p.y = Math.max(20, Math.min(window.innerHeight - 100, p.y));

      if (moved) {
        if (s === "wander" || s === "follow") {
          const dx = s === "follow" ? mouseRef.current.x - p.x : Math.cos(Math.random() * Math.PI * 2);
          if (Math.abs(dx) > 5) {
            setDirection(dx > 0 ? "right" : "left");
          }
        }

        if (s === "follow" || s === "wander") {
          setTailWag(true);
        }

        posRef.current = p;
        setPos({ ...p });
      } else {
        setTailWag(false);
      }

      raf = requestAnimationFrame(tick);
    };

    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [initialized, isDragging]);

  useEffect(() => {
    const interval = setInterval(() => {
      if (stateRef.current !== "sleep") {
        setEarFlap(true);
        setTimeout(() => setEarFlap(false), 400);
      }
    }, 3000 + Math.random() * 2000);
    return () => clearInterval(interval);
  }, []);

  const handleClick = useCallback((e: React.MouseEvent) => {
    e.stopPropagation();

    const id = ++heartIdRef.current;
    setHearts((prev) => [...prev, { id, x: e.clientX, y: e.clientY }]);
    setTimeout(() => setHearts((prev) => prev.filter((h) => h.id !== id)), 1200);

    setState("happy");
    stateRef.current = "happy";
    setThought("💖");
    setShowThought(true);
    setTimeout(() => setShowThought(false), 1500);

    setTailWag(true);
    setEarFlap(true);
    setTimeout(() => {
      setTailWag(false);
      setEarFlap(false);
    }, 1500);
  }, []);

  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    setIsDragging(true);
    dragOffset.current = {
      x: e.clientX - posRef.current.x,
      y: e.clientY - posRef.current.y,
    };

    const handleMouseMove = (ev: MouseEvent) => {
      const newPos = {
        x: Math.max(20, Math.min(window.innerWidth - 80, ev.clientX - dragOffset.current.x)),
        y: Math.max(20, Math.min(window.innerHeight - 100, ev.clientY - dragOffset.current.y)),
      };
      posRef.current = newPos;
      setPos(newPos);
    };

    const handleMouseUp = () => {
      setIsDragging(false);
      window.removeEventListener("mousemove", handleMouseMove);
      window.removeEventListener("mouseup", handleMouseUp);
    };

    window.addEventListener("mousemove", handleMouseMove);
    window.addEventListener("mouseup", handleMouseUp);
  }, []);

  if (!initialized) return null;

  const isSleeping = state === "sleep";
  const isHappy = state === "happy";
  const bounceClass = state === "idle" ? "pet-bounce" : "";
  const scaleX = direction === "left" ? -1 : 1;

  return (
    <div
      className="fixed z-[9999] select-none"
      style={{ left: pos.x, top: pos.y, pointerEvents: "none" }}
    >
      {hearts.map((h) => (
        <div
          key={h.id}
          className="fixed text-2xl animate-heart-float pointer-events-none"
          style={{ left: h.x - 12, top: h.y - 12 }}
        >
          💖
        </div>
      ))}

      {showThought && (
        <div className="absolute -top-10 left-1/2 -translate-x-1/2 thought-bubble">
          <span className="text-lg">{thought}</span>
        </div>
      )}

      {isSleeping && zCount > 0 && (
        <div className="absolute -top-8 right-0 flex gap-1 zzz-container">
          {Array.from({ length: zCount }).map((_, i) => (
            <span
              key={i}
              className="text-blue-400 font-bold zzz-float"
              style={{
                fontSize: 12 + i * 3,
                animationDelay: `${i * 0.3}s`,
                opacity: 0.4 + i * 0.2,
              }}
            >
              z
            </span>
          ))}
        </div>
      )}

      {/* 玉桂狗 SVG - 准确外观 */}
      <div
        className={`cursor-pointer pointer-events-auto ${bounceClass} ${isHappy ? "pet-happy" : ""}`}
        style={{
          transform: `scaleX(${scaleX})`,
          transition: isDragging ? "none" : undefined,
        }}
        onClick={handleClick}
        onMouseDown={handleMouseDown}
      >
        <svg
          width="80"
          height="120"
          viewBox="0 0 200 300"
          xmlns="http://www.w3.org/2000/svg"
          style={{
            filter: isSleeping ? "brightness(0.9) saturate(0.8)" : undefined,
            transition: "filter 0.5s",
          }}
        >
          {/* 左耳 - 超长垂耳，从头顶垂到身体 */}
          <g
            className={earFlap ? "ear-flap-left" : ""}
            style={{ transformOrigin: "70px 100px" }}
          >
            <path
              d="M 65 105 Q 50 70 40 40 Q 35 20 45 15 Q 55 10 58 35 Q 62 60 65 90"
              fill="white"
              stroke="#DDD0D8"
              strokeWidth="1.5"
            />
            <path
              d="M 63 95 Q 52 65 45 40 Q 42 25 50 20 Q 58 18 60 40 Q 62 60 64 85"
              fill="#FFE4EC"
              opacity="0.5"
            />
          </g>

          {/* 右耳 - 超长垂耳 */}
          <g
            className={earFlap ? "ear-flap-right" : ""}
            style={{ transformOrigin: "130px 100px" }}
          >
            <path
              d="M 135 105 Q 150 70 160 40 Q 165 20 155 15 Q 145 10 142 35 Q 138 60 135 90"
              fill="white"
              stroke="#DDD0D8"
              strokeWidth="1.5"
            />
            <path
              d="M 137 95 Q 148 65 155 40 Q 158 25 150 20 Q 142 18 140 40 Q 138 60 136 85"
              fill="#FFE4EC"
              opacity="0.5"
            />
          </g>

          {/* 身体 - 白色圆润短小 */}
          <ellipse cx="100" cy="200" rx="40" ry="45" fill="white" stroke="#DDD0D8" strokeWidth="1.5" />

          {/* 头部 - 大而圆 */}
          <ellipse cx="100" cy="110" rx="58" ry="52" fill="white" stroke="#DDD0D8" strokeWidth="1.5" />

          {/* 腮红 - 明显的粉红色圆形 */}
          <ellipse cx="58" cy="120" rx="12" ry="8" fill="#FFB6C1" opacity={isHappy ? "0.9" : "0.7"} />
          <ellipse cx="142" cy="120" rx="12" ry="8" fill="#FFB6C1" opacity={isHappy ? "0.9" : "0.7"} />

          {/* 眼睛 - 黑色，半月形/弯月形 */}
          {isSleeping ? (
            <>
              {/* 闭眼 - 弯弯的微笑弧线 */}
              <path d="M 80 108 Q 87 102 94 108" fill="none" stroke="#2D2D2D" strokeWidth="2.5" strokeLinecap="round" />
              <path d="M 106 108 Q 113 102 120 108" fill="none" stroke="#2D2D2D" strokeWidth="2.5" strokeLinecap="round" />
            </>
          ) : isBlinking ? (
            <>
              <line x1="80" y1="108" x2="94" y2="108" stroke="#2D2D2D" strokeWidth="2.5" strokeLinecap="round" />
              <line x1="106" y1="108" x2="120" y2="108" stroke="#2D2D2D" strokeWidth="2.5" strokeLinecap="round" />
            </>
          ) : (
            <>
              {/* 左眼 - 大而圆，黑色 */}
              <ellipse cx="87" cy="106" rx="8" ry="9" fill="#2D2D2D" />
              {/* 高光 */}
              <ellipse cx="84" cy="103" rx="2.5" ry="3" fill="white" />
              <ellipse cx="90" cy="108" rx="1.2" ry="1.5" fill="white" opacity="0.6" />
              
              {/* 右眼 - 大而圆，黑色 */}
              <ellipse cx="113" cy="106" rx="8" ry="9" fill="#2D2D2D" />
              {/* 高光 */}
              <ellipse cx="110" cy="103" rx="2.5" ry="3" fill="white" />
              <ellipse cx="116" cy="108" rx="1.2" ry="1.5" fill="white" opacity="0.6" />
            </>
          )}

          {/* 鼻子 - 小巧黑色 */}
          <ellipse cx="100" cy="118" rx="3.5" ry="2.5" fill="#2D2D2D" />

          {/* 嘴巴 - w形或微笑曲线 */}
          {isHappy ? (
            <path d="M 93 123 Q 97 128 100 125 Q 103 128 107 123" fill="none" stroke="#2D2D2D" strokeWidth="1.8" strokeLinecap="round" />
          ) : (
            <path d="M 95 123 Q 100 127 105 123" fill="none" stroke="#2D2D2D" strokeWidth="1.5" strokeLinecap="round" />
          )}

          {/* 蝴蝶结 - 蓝色，头顶偏右 */}
          <g transform="translate(115, 72)">
            <path d="M -2 0 C -6 -10 -18 -12 -15 -3 C -18 5 -6 7 -2 0" fill="#87CEEB" stroke="#6BB8D6" strokeWidth="1" />
            <path d="M 2 0 C 6 -10 18 -12 15 -3 C 18 5 6 7 2 0" fill="#87CEEB" stroke="#6BB8D6" strokeWidth="1" />
            <circle cx="0" cy="0" r="3" fill="#6BB8D6" />
          </g>

          {/* 小手 - 短小圆润 */}
          <ellipse cx="65" cy="195" rx="8" ry="6" fill="white" stroke="#DDD0D8" strokeWidth="1.2" transform="rotate(-10, 65, 195)" />
          <ellipse cx="135" cy="195" rx="8" ry="6" fill="white" stroke="#DDD0D8" strokeWidth="1.2" transform="rotate(10, 135, 195)" />

          {/* 小脚 - 短小圆润 */}
          <ellipse cx="82" cy="242" rx="14" ry="8" fill="white" stroke="#DDD0D8" strokeWidth="1.2" />
          <ellipse cx="118" cy="242" rx="14" ry="8" fill="white" stroke="#DDD0D8" strokeWidth="1.2" />

          {/* 尾巴 - 短小绒球状 */}
          <g className={tailWag ? "tail-wag" : ""} style={{ transformOrigin: "140px 210px" }}>
            <circle cx="148" cy="208" r="12" fill="white" stroke="#DDD0D8" strokeWidth="1.2" />
          </g>
        </svg>
      </div>

      <div className="text-center mt-0.5">
        <span className="text-[10px] text-pink-300 font-medium opacity-70">Cinnamoroll</span>
      </div>

      <style jsx>{`
        .pet-bounce {
          animation: pet-float 2.5s ease-in-out infinite;
        }
        @keyframes pet-float {
          0%, 100% { transform: translateY(0); }
          50% { transform: translateY(-6px); }
        }

        .pet-happy {
          animation: pet-jump 0.4s ease-in-out 3;
        }
        @keyframes pet-jump {
          0%, 100% { transform: translateY(0) rotate(0deg); }
          25% { transform: translateY(-12px) rotate(-5deg); }
          75% { transform: translateY(-12px) rotate(5deg); }
        }

        .tail-wag {
          animation: wag 0.3s ease-in-out infinite alternate;
        }
        @keyframes wag {
          0% { transform: rotate(-8deg); }
          100% { transform: rotate(8deg); }
        }

        .ear-flap-left {
          animation: ear-flap-l 0.4s ease-in-out;
        }
        .ear-flap-right {
          animation: ear-flap-r 0.4s ease-in-out;
        }
        @keyframes ear-flap-l {
          0%, 100% { transform: rotate(0deg); }
          50% { transform: rotate(5deg); }
        }
        @keyframes ear-flap-r {
          0%, 100% { transform: rotate(0deg); }
          50% { transform: rotate(-5deg); }
        }

        .thought-bubble {
          animation: thought-pop 0.3s ease-out;
          background: white;
          border-radius: 20px;
          padding: 4px 10px;
          box-shadow: 0 2px 8px rgba(0,0,0,0.1);
          border: 1px solid #FFE4EC;
        }
        @keyframes thought-pop {
          0% { transform: translateX(-50%) scale(0) translateY(10px); opacity: 0; }
          100% { transform: translateX(-50%) scale(1) translateY(0); opacity: 1; }
        }

        .zzz-float {
          animation: zzz-rise 1.5s ease-out infinite;
        }
        @keyframes zzz-rise {
          0% { transform: translateY(0) translateX(0); opacity: 0.8; }
          100% { transform: translateY(-25px) translateX(10px); opacity: 0; }
        }

        .animate-heart-float {
          animation: heart-float 1.2s ease-out forwards;
          pointer-events: none;
        }
        @keyframes heart-float {
          0% { transform: translateY(0) scale(0.5); opacity: 1; }
          50% { transform: translateY(-30px) scale(1.2); opacity: 0.8; }
          100% { transform: translateY(-60px) scale(0.8); opacity: 0; }
        }
      `}</style>
    </div>
  );
}
