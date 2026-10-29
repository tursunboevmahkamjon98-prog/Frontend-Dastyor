"use client";

import { useRef } from "react";
import { Canvas, useFrame } from "@react-three/fiber";
import { Float, RoundedBox } from "@react-three/drei";
import type { Group } from "three";

/* Replaces an earlier attempt at a 3D character mascot — a hand-built
 * humanoid from spheres/capsules reads as a weird blob rather than a cute
 * robot, and getting a face right needs iteration no amount of math gets
 * you to. A fanned stack of document cards avoids the problem entirely:
 * it's abstract, so there's no "is this cute" bar to clear, and it's
 * literally what the product makes (notes/tests/slides), so it's on-brief
 * rather than decorative. */

type CardSpec = {
  position: [number, number, number];
  rotation: [number, number, number];
  size: [number, number, number];
  accent: string;
  lines?: boolean;
};

const CARDS: CardSpec[] = [
  { position: [-0.55, -0.35, -0.6], rotation: [0.1, 0.5, -0.22], size: [1.5, 1.9, 0.08], accent: "#ec4899" },
  { position: [0.5, -0.15, -0.3], rotation: [0.08, -0.35, 0.16], size: [1.5, 1.9, 0.08], accent: "#3b82f6" },
  { position: [0, 0.1, 0.25], rotation: [0.06, 0.08, -0.05], size: [1.65, 2.05, 0.1], accent: "#dc2626", lines: true },
];

function Card({ position, rotation, size, accent, lines }: CardSpec) {
  const [w, h, d] = size;
  return (
    <group position={position} rotation={rotation}>
      <RoundedBox args={[w, h, d]} radius={0.09} smoothness={4} castShadow>
        <meshPhysicalMaterial color="#ffffff" roughness={0.3} clearcoat={0.6} clearcoatRoughness={0.25} />
      </RoundedBox>
      {/* Accent header strip */}
      <mesh position={[0, h / 2 - 0.22, d / 2 + 0.005]}>
        <boxGeometry args={[w - 0.3, 0.22, 0.02]} />
        <meshStandardMaterial color={accent} />
      </mesh>
      {lines && (
        <>
          <mesh position={[-0.12, 0.05, d / 2 + 0.005]}>
            <boxGeometry args={[w - 0.55, 0.09, 0.015]} />
            <meshStandardMaterial color="#f3d9d8" />
          </mesh>
          <mesh position={[-0.22, -0.22, d / 2 + 0.005]}>
            <boxGeometry args={[w - 0.75, 0.09, 0.015]} />
            <meshStandardMaterial color="#f3d9d8" />
          </mesh>
          <mesh position={[-0.05, -0.49, d / 2 + 0.005]}>
            <boxGeometry args={[w - 0.4, 0.09, 0.015]} />
            <meshStandardMaterial color="#f3d9d8" />
          </mesh>
        </>
      )}
    </group>
  );
}

function CardStack() {
  const group = useRef<Group>(null);
  useFrame((_, delta) => {
    if (group.current) group.current.rotation.y += delta * 0.15;
  });

  return (
    <Float speed={1.2} rotationIntensity={0.12} floatIntensity={0.55}>
      <group ref={group}>
        {CARDS.map((card, i) => (
          <Card key={i} {...card} />
        ))}
      </group>
    </Float>
  );
}

export default function MaterialCards3D({ className }: { className?: string }) {
  return (
    <div className={className}>
      <Canvas camera={{ position: [0, 0.3, 5.2], fov: 32 }} dpr={[1, 2]}>
        <ambientLight intensity={0.9} />
        <directionalLight position={[3, 5, 4]} intensity={1.15} />
        <directionalLight position={[-4, 1, -3]} intensity={0.35} color="#ffd9d9" />
        <pointLight position={[0, -1, 3]} intensity={0.2} color="#ffe4e4" />
        <CardStack />
      </Canvas>
    </div>
  );
}
