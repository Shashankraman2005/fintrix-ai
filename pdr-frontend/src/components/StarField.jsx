import React, { useRef } from 'react';
import { motion, useScroll, useTransform } from 'framer-motion';

export default function StarField() {
  const { scrollY } = useScroll();
  const stars = useRef([]);

  if (stars.current.length === 0) {
    for (let i = 0; i < 1200; i++) {
      const tier = Math.random();
      const isSuperBright = tier < 0.06;
      const isBright      = tier < 0.22;
      stars.current.push({
        id: i,
        x: Math.random() * 100,
        y: Math.random() * 500,
        size: isSuperBright
          ? Math.random() * 4 + 3
          : isBright
          ? Math.random() * 2 + 1.5
          : Math.random() * 1.2 + 0.6,
        baseOpacity: isSuperBright ? 1 : isBright ? 0.85 : Math.random() * 0.55 + 0.4,
        depth: Math.random() * 0.8 + 0.2,
        twinkleDelay: Math.random() * 6,
        twinkleDuration: isSuperBright ? 1.2 + Math.random() * 1.5 : 2 + Math.random() * 3,
        isSuperBright,
        isBright,
        color: Math.random() < 0.2
          ? `rgba(180,210,255,1)`
          : Math.random() < 0.1
          ? `rgba(255,230,180,1)`
          : `rgba(255,255,255,1)`,
      });
    }
  }

  const layer1Y = useTransform(scrollY, [0, 4000], [0, -150]);
  const layer2Y = useTransform(scrollY, [0, 4000], [0, -300]);
  const layer3Y = useTransform(scrollY, [0, 4000], [0, -500]);

  const layers = [
    { stars: stars.current.filter(s => s.depth < 0.4), y: layer1Y },
    { stars: stars.current.filter(s => s.depth >= 0.4 && s.depth < 0.7), y: layer2Y },
    { stars: stars.current.filter(s => s.depth >= 0.7), y: layer3Y },
  ];

  return (
    <div className="fixed inset-0 pointer-events-none z-0 overflow-hidden">
      {layers.map((layer, li) => (
        <motion.div key={li} style={{ y: layer.y }} className="absolute inset-0">
          {layer.stars.map(star => (
            <motion.div
              key={star.id}
              className="absolute rounded-full"
              style={{
                left: `${star.x}%`,
                top: `${star.y}vh`,
                width: star.size,
                height: star.size,
                background: star.isSuperBright
                  ? `radial-gradient(circle, #ffffff 0%, ${star.color.replace('1)', '0.7)')} 50%, transparent 100%)`
                  : star.color,
                boxShadow: star.isSuperBright
                  ? `0 0 ${star.size * 5}px ${star.size * 2}px rgba(180,220,255,0.9), 0 0 ${star.size * 10}px ${star.size * 3}px rgba(150,200,255,0.4)`
                  : star.isBright
                  ? `0 0 ${star.size * 3}px ${star.size}px rgba(200,225,255,0.7)`
                  : 'none',
              }}
              animate={{ opacity: [star.baseOpacity, star.baseOpacity * 0.1, star.baseOpacity] }}
              transition={{
                duration: star.twinkleDuration,
                repeat: Infinity,
                delay: star.twinkleDelay,
                ease: 'easeInOut',
              }}
            />
          ))}
        </motion.div>
      ))}
    </div>
  );
}
