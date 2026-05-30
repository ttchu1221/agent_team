"use client";

import { useEffect, useRef, useState, useCallback } from "react";

// ============================================================
//  玉桂狗 (Cinnamoroll) 虚拟宠物组件
//  更准确的外观 - 蓝色眼睛、长耳朵、粉色腮红
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

  // 初始化位置
  useEffect(() => {
    if (typeof window === "undefined") return;
    const x = window.innerWidth - 120;
    const y = window.innerHeight - 160;
    posRef.current = { x, y };
    setPos({ x, y });
    setInitialized(true);
  }, []);

  // 追踪鼠标
  useEffect(() => {
    const handleMouse = (e: MouseEvent) => {
      mouseRef.current = { x: e.clientX, y: e.clientY };
    };
    window.addEventListener("mousemove", handleMouse);
    return () => window.removeEventListener("mousemove", handleMouse);
  }, []);

  // 眨眼动画
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

  // 状态机：随机切换行为
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

  // 移动循环
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

  // 耳朵拍动
  useEffect(() => {
    const interval = setInterval(() => {
      if (stateRef.current !== "sleep") {
        setEarFlap(true);
        setTimeout(() => setEarFlap(false), 400);
      }
    }, 3000 + Math.random() * 2000);
    return () => clearInterval(interval);
  }, []);

  // 点击互动
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

  // 拖拽
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
      {/* 爱心特效 */}
      {hearts.map((h) => (
        <div
          key={h.id}
          className="fixed text-2xl animate-heart-float pointer-events-none"
          style={{ left: h.x - 12, top: h.y - 12 }}
        >
          💖
        </div>
      ))}

      {/* 想法气泡 */}
      {showThought && (
        <div className="absolute -top-10 left-1/2 -translate-x-1/2 thought-bubble">
          <span className="text-lg">{thought}</span>
        </div>
      )}

      {/* Zzz 动画 */}
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

      {/* 玉桂狗 SVG - 更准确的外观 */}
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
          height="100"
          viewBox="0 0 200 250"
          xmlns="http://www.w3.org/2000/svg"
          style={{
            filter: isSleeping ? "brightness(0.9) saturate(0.8)" : undefined,
            transition: "filter 0.5s",
          }}
        >
          {/* 左耳 - 长而柔软，下垂 */}
          <g
            className={earFlap ? "ear-flap-left" : ""}
            style={{ transformOrigin: "75px 90px" }}
          >
            <path
              d="M 70 95 Q 55 60 45 30 Q 40 15 50 10 Q 60 5 65 25 Q 70 50 72 80"
              fill="white"
              stroke="#E8D5E0"
              strokeWidth="2"
            />
            <path
              d="M 68 85 Q 58 55 52 30 Q 48 18 55 15 Q 62 12 65 35 Q 68 55 70 75"
              fill="#FFE8F0"
              opacity="0.4"
            />
          </g>

          {/* 右耳 - 长而柔软，下垂 */}
          <g
            className={earFlap ? "ear-flap-right" : ""}
            style={{ transformOrigin: "125px 90px" }}
          >
            <path
              d="M 130 95 Q 145 60 155 30 Q 160 15 150 10 Q 140 5 135 25 Q 130 50 128 80"
              fill="white"
              stroke="#E8D5E0"
              strokeWidth="2"
            />
            <path
              d="M 132 85 Q 142 55 148 30 Q 152 18 145 15 Q 138 12 135 35 Q 132 55 130 75"
              fill="#FFE8F0"
              opacity="0.4"
            />
          </g>

          {/* 身体 - 白色圆润 */}
          <ellipse cx="100" cy="175" rx="45" ry="50" fill="white" stroke="#E8D5E0" strokeWidth="2" />
          
          {/* 头部 - 圆润白色 */}
          <ellipse cx="100" cy="100" rx="55" ry="48" fill="white" stroke="#E8D5E0" strokeWidth="2" />

          {/* 腮红 - 明显的粉色 */}
          <ellipse cx="60" cy="110" rx="14" ry="9" fill="#FFB6C1" opacity={isHappy ? "0.9" : "0.6"} />
          <ellipse cx="140" cy="110" rx="14" ry="9" fill="#FFB6C1" opacity={isHappy ? "0.9" : "0.6"} />

          {/* 眼睛 - 大而圆，蓝色瞳孔 */}
          {isSleeping ? (
            <>
              {/* 闭眼 - 弯弯的弧线 */}
              <path d="M 78 98 Q 85 92 92 98" fill="none" stroke="#2E4057" strokeWidth="2.5" strokeLinecap="round" />
              <path d="M 108 98 Q 115 92 122 98" fill="none" stroke="#2E4057" strokeWidth="2.5" strokeLinecap="round" />
            </>
          ) : isBlinking ? (
            <>
              {/* 眨眼 */}
              <line x1="78" y1="98" x2="92" y2="98" stroke="#2E4057" strokeWidth="2.5" strokeLinecap="round" />
              <line x1="108" y1="98" x2="122" y2="98" stroke="#2E4057" strokeWidth="2.5" strokeLinecap="round" />
            </>
          ) : (
            <>
              {/* 左眼 */}
              <ellipse cx="85" cy="96" rx="10" ry="11" fill="#4A90D9" />
              <ellipse cx="85" cy="96" rx="7" ry="8" fill="#2E5B8C" />
              <ellipse cx="85" cy="95" rx="4" ry="4.5" fill="#1A3A5C" />
              {/* 高光 */}
              <ellipse cx="82" cy="92" rx="3" ry="3.5" fill="white" />
              <ellipse cx="88" cy="98" rx="1.5" ry="2" fill="white" opacity="0.7" />
              
              {/* 右眼 */}
              <ellipse cx="115" cy="96" rx="10" ry="11" fill="#4A90D9" />
              <ellipse cx="115" cy="96" rx="7" ry="8" fill="#2E5B8C" />
              <ellipse cx="115" cy="95" rx="4" ry="4.5" fill="#1A3A5C" />
              {/* 高光 */}
              <ellipse cx="112" cy="92" rx="3" ry="3.5" fill="white" />
              <ellipse cx="118" cy="98" rx="1.5" ry="2" fill="white" opacity="0.7" />
            </>
          )}

          {/* 鼻子 - 小巧粉色 */}
          <ellipse cx="100" cy="108" rx="4" ry="3" fill="#FFB6C1" />

          {/* 嘴巴 - 微笑 */}
          {isHappy ? (
            <path d="M 92 113 Q 100 122 108 113" fill="none" stroke="#2E4057" strokeWidth="2" strokeLinecap="round" />
          ) : (
            <path d="M 95 113 Q 100 118 105 113" fill="none" stroke="#2E4057" strokeWidth="1.8" strokeLinecap="round" />
          )}

          {/* 蝴蝶结 - 蓝色，头顶 */}
          <g transform="translate(100, 62)">
            {/* 左翼 */}
            <path d="M -2 0 C -8 -12 -22 -14 -18 -4 C -22 6 -8 8 -2 0" fill="#87CEEB" stroke="#5BA3C7" strokeWidth="1" />
            {/* 右翼 */}
            <path d="M 2 0 C 8 -12 22 -14 18 -4 C 22 6 8 8 2 0" fill="#87CEEB" stroke="#5BA3C7" strokeWidth="1" />
            {/* 中心结 */}
            <circle cx="0" cy="0" r="4" fill="#5BA3C7" />
            <circle cx="0" cy="0" r="2" fill="#87CEEB" />
          </g>

          {/* 小手 - 圆润 */}
          <ellipse cx="60" cy="168" rx="10" ry="7" fill="white" stroke="#E8D5E0" strokeWidth="1.5" transform="rotate(-15, 60, 168)" />
          <ellipse cx="140" cy="168" rx="10" ry="7" fill="white" stroke="#E8D5E0" strokeWidth="1.5" transform="rotate(15, 140, 168)" />

          {/* 小脚 - 圆润 */}
          <ellipse cx="78" cy="220" rx="16" ry="9" fill="white" stroke="#E8D5E0" strokeWidth="1.5" />
          <ellipse cx="122" cy="220" rx="16" ry="9" fill="white" stroke="#E8D5E0" strokeWidth="1.5" />

          {/* 尾巴 - 肉桂卷形状 */}
          <g className={tailWag ? "tail-wag" : ""} style={{ transformOrigin: "142px 185px" }}>
            <path
              d="M 142 185 C 160 180 168 170 165 160 C 162 150 152 152 155 162 C 158 170 150 175 145 180"
              fill="white"
              stroke="#E8D5E0"
              strokeWidth="2"
              strokeLinecap="round"
            />
          </g>
        </svg>
      </div>

      {/* 宠物名字标签 */}
      <div className="text-center mt-0.5">
        <span className="text-[10px] text-blue-300 font-medium opacity-70">Cinnamoroll</span>
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
          0% { transform: rotate(-10deg); }
          100% { transform: rotate(10deg); }
        }

        .ear-flap-left {
          animation: ear-flap-l 0.4s ease-in-out;
        }
        .ear-flap-right {
          animation: ear-flap-r 0.4s ease-in-out;
        }
        @keyframes ear-flap-l {
          0%, 100% { transform: rotate(0deg); }
          50% { transform: rotate(8deg); }
        }
        @keyframes ear-flap-r {
          0%, 100% { transform: rotate(0deg); }
          50% { transform: rotate(-8deg); }
        }

        .thought-bubble {
          animation: thought-pop 0.3s ease-out;
          background: white;
          border-radius: 20px;
          padding: 4px 10px;
          box-shadow: 0 2px 8px rgba(0,0,0,0.1);
          border: 1px solid #E8D5E0;
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
