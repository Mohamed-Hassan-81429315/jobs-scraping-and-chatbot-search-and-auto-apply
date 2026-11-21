'use client';
import { useEffect, useState } from 'react';

export default function Counter({ value = 0, duration = 1200 }) {
  const [n, setN] = useState(0);

  useEffect(() => {
    let raf;
    const start = performance.now();
    const tick = (now) => {
      const p = Math.min((now - start) / duration, 1);
      setN(Math.floor(value * (1 - Math.pow(1 - p, 3))));
      if (p < 1) raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [value, duration]);

  return <span>{n.toLocaleString()}</span>;
}