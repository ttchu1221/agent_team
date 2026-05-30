"use client";

import { useEffect, useRef, useState, useCallback } from "react";

// ============================================================
//  玉桂狗 (Cinnamoroll) 虚拟宠物组件
//  纯 SVG + CSS 动画，无外部图片依赖
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
      // 30% 概率跟随鼠标
      const distToMouse = Math.hypot(
        mouseRef.current.x - posRef.current.x,
        mouseRef.current.y - posRef.current.y
      );

      let nextState: PetState;
      if (distToMouse < 200 && Math.random() < 0.35) {
        nextState = "follow";
      } else {
        const pool: PetState[] = ["idle", "wander", "idle", "wander", "sleep", "play"];
        // 距离鼠标近时增加 follow 概率
        if (distToMouse < 350) pool.push("follow");
        nextState = pool[Math.floor(Math.random() * pool.length)];
      }

      setState(nextState);
      stateRef.current = nextState;

      // 显示想法气泡
      const thoughts = THOUGHTS[nextState];
      setThought(thoughts[Math.floor(Math.random() * thoughts.length)]);
      setShowThought(true);
      setTimeout(() => setShowThought(false), 2000);

      // sleep 时显示 Zzz
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
        // 随机漫步
        const angle = Math.random() * Math.PI * 2;
        p.x += Math.cos(angle) * speed * 2;
        p.y += Math.sin(angle) * speed * 2;
        moved = true;
      } else if (s === "follow") {
        // 缓慢靠近鼠标
        const dx = mouseRef.current.x - p.x;
        const dy = mouseRef.current.y - p.y;
        const dist = Math.hypot(dx, dy);
        if (dist > 60) {
          p.x += (dx / dist) * speed * 1.5;
          p.y += (dy / dist) * speed * 1.5;
          moved = true;
        }
      } else if (s === "idle") {
        // 轻微浮动
        p.y += Math.sin(Date.now() / 800) * 0.3;
        moved = true;
      }

      // 边界约束
      p.x = Math.max(20, Math.min(window.innerWidth - 80, p.x));
      p.y = Math.max(20, Math.min(window.innerHeight - 100, p.y));

      if (moved) {
        // 方向
        if (s === "wander" || s === "follow") {
          const dx = s === "follow" ? mouseRef.current.x - p.x : Math.cos(Math.random() * Math.PI * 2);
          if (Math.abs(dx) > 5) {
            setDirection(dx > 0 ? "right" : "left");
          }
        }

        // 摇尾巴
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

    // 爱心特效
    const id = ++heartIdRef.current;
    setHearts((prev) => [...prev, { id, x: e.clientX, y: e.clientY }]);
    setTimeout(() => setHearts((prev) => prev.filter((h) => h.id !== id)), 1200);

    // 切换到 happy
    setState("happy");
    stateRef.current = "happy";
    setThought("💖");
    setShowThought(true);
    setTimeout(() => setShowThought(false), 1500);

    // 摇尾巴 + 拍耳朵
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

      {/* 玉桂狗 SVG */}
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
          {/* 左耳 */}
          <g
            className={earFlap ? "ear-flap-left" : ""}
            style={{ transformOrigin: "70px 100px" }}
          >
            <path
              d="M 60 105 Q 30 40 55 15 Q 70 5 75 40 Q 80 70 75 100"
              fill="white"
              stroke="#E8D5E0"
              strokeWidth="2"
            />
            <path
              d="M 58 90 Q 40 45 58 25 Q 68 18 72 45 Q 75 70 73 90"
              fill="#FFE4F0"
              opacity="0.5"
            />
          </g>

          {/* 右耳 */}
          <g
            className={earFlap ? "ear-flap-right" : ""}
            style={{ transformOrigin: "130px 100px" }}
          >
            <path
              d="M 140 105 Q 170 40 145 15 Q 130 5 125 40 Q 120 70 125 100"
              fill="white"
              stroke="#E8D5E0"
              strokeWidth="2"
            />
            <path
              d="M 142 90 Q 160 45 142 25 Q 132 18 128 45 Q 125 70 127 90"
              fill="#FFE4F0"
              opacity="0.5"
            />
          </g>

          {/* 身体（白色蓬松） */}
          <ellipse cx="100" cy="170" rx="48" ry="55" fill="white" stroke="#E8D5E0" strokeWidth="2" />
          <ellipse cx="100" cy="172" rx="40" ry="45" fill="white" />

          {/* 头部 */}
          <ellipse cx="100" cy="105" rx="52" ry="45" fill="white" stroke="#E8D5E0" strokeWidth="2" />
          <ellipse cx="100" cy="107" rx="48" ry="40" fill="white" />

          {/* 腮红 */}
          <ellipse cx="65" cy="115" rx="10" ry="6" fill="#FFB6C1" opacity={isHappy ? "0.8" : "0.4"} />
          <ellipse cx="135" cy="115" rx="10" ry="6" fill="#FFB6C1" opacity={isHappy ? "0.8" : "0.4"} />

          {/* 眼睛 */}
          {isSleeping ? (
            <>
              {/* 闭眼 */}
              <path d="M 82 105 Q 87 100 92 105" fill="none" stroke="#4A4A6A" strokeWidth="2.5" strokeLinecap="round" />
              <path d="M 108 105 Q 113 100 118 105" fill="none" stroke="#4A4A6A" strokeWidth="2.5" strokeLinecap="round" />
            </>
          ) : isBlinking ? (
            <>
              {/* 眨眼 */}
              <line x1="82" y1="105" x2="92" y2="105" stroke="#4A4A6A" strokeWidth="2.5" strokeLinecap="round" />
              <line x1="108" y1="105" x2="118" y2="105" stroke="#4A4A6A" strokeWidth="2.5" strokeLinecap="round" />
            </>
          ) : (
            <>
              {/* 睁眼 - 大而圆 */}
              <ellipse cx="87" cy="103" rx="7" ry="8" fill="#4A4A6A" />
              <ellipse cx="113" cy="103" rx="7" ry="8" fill="#4A4A6A" />
              {/* 眼睛高光 */}
              <ellipse cx="85" cy="100" rx="2.5" ry="3" fill="white" />
              <ellipse cx="111" cy="100" rx="2.5" ry="3" fill="white" />
              <ellipse cx="89" cy="105" rx="1.2" ry="1.5" fill="white" opacity="0.7" />
              <ellipse cx="115" cy="105" rx="1.2" ry="1.5" fill="white" opacity="0.7" />
            </>
          )}

          {/* 鼻子 */}
          <ellipse cx="100" cy="112" rx="3" ry="2" fill="#FFB6C1" />

          {/* 嘴巴 */}
          {isHappy ? (
            <>
              <path d="M 94 117 Q 100 124 106 117" fill="none" stroke="#4A4A6A" strokeWidth="1.8" strokeLinecap="round" />
            </>
          ) : (
            <>
              <path d="M 97 117 Q 100 120 103 117" fill="none" stroke="#4A4A6A" strokeWidth="1.5" strokeLinecap="round" />
            </>
          )}

          {/* 蝴蝶结 */}
          <g transform="translate(100, 78)">
            <path d="M -3 0 Q -15 -10 -12 -2 Q -15 6 -3 0" fill="#87CEEB" stroke="#6BB3D9" strokeWidth="1" />
            <path d="M 3 0 Q 15 -10 12 -2 Q 15 6 3 0" fill="#87CEEB" stroke="#6BB3D9" strokeWidth="1" />
            <circle cx="0" cy="0" r="3" fill="#6BB3D9" />
          </g>

          {/* 小手 */}
          <ellipse cx="62" cy="165" rx="8" ry="6" fill="white" stroke="#E8D5E0" strokeWidth="1.5"
            transform="rotate(-20, 62, 165)" />
          <ellipse cx="138" cy="165" rx="8" ry="6" fill="white" stroke="#E8D5E0" strokeWidth="1.5"
            transform="rotate(20, 138, 165)" />

          {/* 小脚 */}
          <ellipse cx="80" cy="218" rx="14" ry="8" fill="white" stroke="#E8D5E0" strokeWidth="1.5" />
          <ellipse cx="120" cy="218" rx="14" ry="8" fill="white" stroke="#E8D5E0" strokeWidth="1.5" />

          {/* 尾巴（肉桂卷） */}
          <g className={tailWag ? "tail-wag" : ""} style={{ transformOrigin: "145px 190px" }}>
            <path
              d="M 145 190 Q 165 185 168 175 Q 170 165 162 168 Q 155 170 158 178 Q 160 183 152 185"
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
        <span className="text-[10px] text-pink-300 font-medium opacity-70">Cinnamoroll</span>
      </div>

      <style jsx>{`
        /* 浮动动画 */
        .pet-bounce {
          animation: pet-float 2.5s ease-in-out infinite;
        }
        @keyframes pet-float {
          0%, 100% { transform: translateY(0); }
          50% { transform: translateY(-6px); }
        }

        /* 开心跳 */
        .pet-happy {
          animation: pet-jump 0.4s ease-in-out 3;
        }
        @keyframes pet-jump {
          0%, 100% { transform: translateY(0) rotate(0deg); }
          25% { transform: translateY(-12px) rotate(-5deg); }
          75% { transform: translateY(-12px) rotate(5deg); }
        }

        /* 摇尾巴 */
        .tail-wag {
          animation: wag 0.3s ease-in-out infinite alternate;
        }
        @keyframes wag {
          0% { transform: rotate(-10deg); }
          100% { transform: rotate(10deg); }
        }

        /* 耳朵拍动 */
        .ear-flap-left {
          animation: ear-flap-l 0.4s ease-in-out;
        }
        .ear-flap-right {
          animation: ear-flap-r 0.4s ease-in-out;
        }
        @keyframes ear-flap-l {
          0%, 100% { transform: rotate(0deg); }
          50% { transform: rotate(12deg); }
        }
        @keyframes ear-flap-r {
          0%, 100% { transform: rotate(0deg); }
          50% { transform: rotate(-12deg); }
        }

        /* 想法气泡 */
        .thought-bubble {
          animation: thought-pop 0.3s ease-out;
          background: white;
          border-radius: 20px;
          padding: 4px 10px;
          box-shadow: 0 2px 8px rgba(0,0,0,0.1);
          border: 1px solid #f0e0f0;
        }
        @keyframes thought-pop {
          0% { transform: translateX(-50%) scale(0) translateY(10px); opacity: 0; }
          100% { transform: translateX(-50%) scale(1) translateY(0); opacity: 1; }
        }

        /* Zzz 浮动 */
        .zzz-float {
          animation: zzz-rise 1.5s ease-out infinite;
        }
        @keyframes zzz-rise {
          0% { transform: translateY(0) translateX(0); opacity: 0.8; }
          100% { transform: translateY(-25px) translateX(10px); opacity: 0; }
        }

        /* 爱心浮动 */
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
