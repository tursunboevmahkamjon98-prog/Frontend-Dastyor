"use client";

import { useRef } from "react";
import { Canvas, useFrame } from "@react-three/fiber";
import { Float, RoundedBox } from "@react-three/drei";
import type { Group } from "three";

/* A second, distinct 3D asset — not the landing/auth card stack again.
 * Standing columns instead of fanned flat cards gives it its own silhouette,
 * and it's the one spot on the dashboard where tying the 3D piece to real
 * data (bar heights from the user's own material counts) actually earns its
 * place rather than being decoration for its own sake. Oscillates instead of
 * fully spinning — a bar chart that rotates past edge-on stops being
 * readable, which a flat fanned card never has to worry about. */

const COLORS = ["#3b82f6", "#d97706", "#10b981", "#ec4899", "#0d9488"];
const MIN_H = 0.5;
const MAX_H = 2.1;

function normalize(values: number[]): number[] {
  const max = Math.max(1, ...values);
  return values.map((v) => MIN_H + (Math.min(v, max) / max) * (MAX_H - MIN_H));
}

function Bars({ values }: { values: number[] }) {
  const group = useRef<Group>(null);
  useFrame((state) => {
    if (group.current) group.current.rotation.y = Math.sin(state.clock.elapsedTime * 0.3) * 0.35;
  });

  const heights = normalize(values);
  const count = heights.length;
  const gap = 0.62;
  const startX = -((count - 1) * gap) / 2;

  return (
    <Float speed={1.1} rotationIntensity={0.04} floatIntensity={0.45}>
      <group ref={group}>
        {/* Base platform */}
        <RoundedBox args={[count * gap + 0.4, 0.14, 0.7]} radius={0.06} smoothness={4} position={[0, -1.05, 0]}>
          <meshPhysicalMaterial color="#ffffff" roughness={0.4} clearcoat={0.4} />
        </RoundedBox>

        {heights.map((h, i) => (
          <RoundedBox
            key={i}
            args={[0.46, h, 0.46]}
            radius={0.09}
            smoothness={4}
            position={[startX + i * gap, -1.05 + h / 2 + 0.07, 0]}
            castShadow
          >
            <meshPhysicalMaterial color={COLORS[i % COLORS.length]} roughness={0.3} clearcoat={0.5} clearcoatRoughness={0.25} />
          </RoundedBox>
        ))}
      </group>
    </Float>
  );
}

export default function ProgressBars3D({ className, values }: { className?: string; values?: number[] }) {
  const v = values && values.length === 5 ? values : [1, 1, 1, 1, 1];
  return (
    <div className={className}>
      <Canvas camera={{ position: [0, 0.4, 5.2], fov: 32 }} dpr={[1, 2]}>
        <ambientLight intensity={0.9} />
        <directionalLight position={[3, 5, 4]} intensity={1.1} />
        <directionalLight position={[-4, 1, -3]} intensity={0.3} color="#ffd9d9" />
        <pointLight position={[0, -1, 3]} intensity={0.2} color="#ffe4e4" />
        <Bars values={v} />
      </Canvas>
    </div>
  );
}
