"use client";

import { useRef } from "react";
import { Canvas, useFrame } from "@react-three/fiber";
import { Float, RoundedBox } from "@react-three/drei";
import type { Group } from "three";
import { useSceneActivity } from "@/lib/use-scene-activity";

type BookSpec = {
  position: [number, number, number];
  rotation: [number, number, number];
  scale: number;
  cover: string;
  accent: string;
};

const BOOKS: BookSpec[] = [
  { position: [-0.48, 0.08, -0.5], rotation: [0.12, 0.36, -0.18], scale: 0.9, cover: "#7c3aed", accent: "#f472b6" },
  { position: [-0.2, 0.16, 0.04], rotation: [0.08, -0.12, -0.08], scale: 1.06, cover: "#dc2626", accent: "#fbbf24" },
];

function Book({ position, rotation, scale, cover, accent }: BookSpec) {
  return (
    <group position={position} rotation={rotation} scale={scale}>
      {/* Rounded cover and bright page block give the book real thickness. */}
      <RoundedBox args={[1.55, 2.05, 0.25]} radius={0.13} smoothness={6} castShadow>
        <meshPhysicalMaterial color={cover} roughness={0.27} metalness={0.04} clearcoat={0.9} clearcoatRoughness={0.18} emissive={cover} emissiveIntensity={0.08} />
      </RoundedBox>
      <RoundedBox args={[1.43, 1.92, 0.09]} radius={0.075} smoothness={5} position={[0.015, 0, 0.16]}>
        <meshStandardMaterial color="#fffdfa" emissive="#fff8f5" emissiveIntensity={0.24} roughness={0.7} />
      </RoundedBox>
      <RoundedBox args={[1.15, 0.16, 0.025]} radius={0.05} smoothness={4} position={[0, 0.68, 0.22]}>
        <meshStandardMaterial color={accent} emissive={accent} emissiveIntensity={0.1} />
      </RoundedBox>
      <RoundedBox args={[0.92, 0.075, 0.025]} radius={0.03} smoothness={4} position={[-0.1, 0.24, 0.22]}>
        <meshBasicMaterial color="#f1d8d6" />
      </RoundedBox>
      <RoundedBox args={[0.7, 0.075, 0.025]} radius={0.03} smoothness={4} position={[-0.21, -0.03, 0.22]}>
        <meshBasicMaterial color="#f1d8d6" />
      </RoundedBox>
      <RoundedBox args={[1.02, 0.075, 0.025]} radius={0.03} smoothness={4} position={[-0.05, -0.3, 0.22]}>
        <meshBasicMaterial color="#f1d8d6" />
      </RoundedBox>
      <mesh position={[0.43, -0.66, 0.23]}>
        <sphereGeometry args={[0.13, 24, 24]} />
        <meshPhysicalMaterial color={accent} roughness={0.24} clearcoat={0.85} />
      </mesh>
    </group>
  );
}

function GameController({ active }: { active: boolean }) {
  const buttons = [
    { position: [0.34, 0.12, 0.17] as [number, number, number], color: "#f472b6" },
    { position: [0.49, 0, 0.17] as [number, number, number], color: "#fbbf24" },
    { position: [0.19, 0, 0.17] as [number, number, number], color: "#34d399" },
    { position: [0.34, -0.12, 0.17] as [number, number, number], color: "#60a5fa" },
  ];

  return (
    <Float enabled={active} speed={1.4} rotationIntensity={0.08} floatIntensity={0.14}>
      <group position={[0.82, -0.78, 0.82]} rotation={[0.18, -0.24, -0.15]} scale={0.72}>
        <RoundedBox args={[1.42, 0.7, 0.26]} radius={0.28} smoothness={6} castShadow>
          <meshPhysicalMaterial color="#7c3aed" roughness={0.28} metalness={0.08} clearcoat={0.85} clearcoatRoughness={0.18} emissive="#4c1d95" emissiveIntensity={0.12} />
        </RoundedBox>
        <RoundedBox args={[0.48, 0.46, 0.28]} radius={0.22} smoothness={5} position={[-0.43, -0.18, 0.015]}>
          <meshPhysicalMaterial color="#6d28d9" roughness={0.32} clearcoat={0.7} />
        </RoundedBox>
        <RoundedBox args={[0.48, 0.46, 0.28]} radius={0.22} smoothness={5} position={[0.43, -0.18, 0.015]}>
          <meshPhysicalMaterial color="#6d28d9" roughness={0.32} clearcoat={0.7} />
        </RoundedBox>
        <RoundedBox args={[0.34, 0.105, 0.045]} radius={0.035} smoothness={3} position={[-0.37, 0.02, 0.155]}>
          <meshStandardMaterial color="#fff7ff" />
        </RoundedBox>
        <RoundedBox args={[0.105, 0.34, 0.045]} radius={0.035} smoothness={3} position={[-0.37, 0.02, 0.16]}>
          <meshStandardMaterial color="#fff7ff" />
        </RoundedBox>
        {buttons.map((button, i) => (
          <mesh key={i} position={button.position}>
            <sphereGeometry args={[0.07, 20, 20]} />
            <meshPhysicalMaterial color={button.color} roughness={0.24} clearcoat={0.85} />
          </mesh>
        ))}
        <mesh position={[-0.13, -0.02, 0.16]} rotation={[Math.PI / 2, 0, 0]}>
          <cylinderGeometry args={[0.07, 0.07, 0.035, 24]} />
          <meshPhysicalMaterial color="#ddd6fe" roughness={0.35} />
        </mesh>
        <mesh position={[0.07, -0.02, 0.16]} rotation={[Math.PI / 2, 0, 0]}>
          <cylinderGeometry args={[0.07, 0.07, 0.035, 24]} />
          <meshPhysicalMaterial color="#ddd6fe" roughness={0.35} />
        </mesh>
      </group>
    </Float>
  );
}

function LearningScene({ active }: { active: boolean }) {
  const group = useRef<Group>(null);
  useFrame((_, delta) => {
    if (active && group.current) group.current.rotation.y += delta * 0.1;
  });

  return (
    <Float enabled={active} speed={1.1} rotationIntensity={0.1} floatIntensity={0.28}>
      <group ref={group}>
        {BOOKS.map((book, i) => <Book key={i} {...book} />)}
        <mesh position={[-1.15, 0.95, 0.22]} rotation={[0.2, 0.35, 0.15]}>
          <icosahedronGeometry args={[0.17, 0]} />
          <meshPhysicalMaterial color="#fbbf24" roughness={0.22} metalness={0.08} clearcoat={0.9} emissive="#f59e0b" emissiveIntensity={0.14} />
        </mesh>
        <mesh position={[0.98, 0.92, -0.05]} rotation={[0.4, 0.1, -0.2]}>
          <octahedronGeometry args={[0.13]} />
          <meshPhysicalMaterial color="#f472b6" roughness={0.24} clearcoat={0.8} emissive="#ec4899" emissiveIntensity={0.12} />
        </mesh>
        <GameController active={active} />
      </group>
    </Float>
  );
}

export default function MaterialCards3D({ className }: { className?: string }) {
  const { containerRef, entered, active } = useSceneActivity();
  return (
    <div ref={containerRef} className={className}>
      {entered && (
        <Canvas frameloop={active ? "always" : "demand"} camera={{ position: [0, 0.3, 5.2], fov: 32 }} dpr={[1, 2]}>
          <ambientLight intensity={1.15} />
          <directionalLight position={[3, 5, 4]} intensity={1.5} />
          <directionalLight position={[-4, 1, -3]} intensity={0.45} color="#ffd9d9" />
          <pointLight position={[0, -1, 3]} intensity={0.28} color="#ffe4e4" />
          <LearningScene active={active} />
        </Canvas>
      )}
    </div>
  );
}
