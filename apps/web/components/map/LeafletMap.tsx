"use client";

import * as React from "react";
import { LeafletMapInstance } from "@/lib/leaflet-map-provider";
import type { MapMarker } from "@/lib/map-provider";

interface LeafletMapProps {
  center: [number, number];
  zoom?: number;
  markers?: MapMarker[];
  className?: string;
  onMapReady?: (map: LeafletMapInstance) => void;
}

export function LeafletMap({
  center,
  zoom = 15,
  markers = [],
  className = "h-64 w-full rounded-2xl overflow-hidden",
  onMapReady,
}: LeafletMapProps) {
  const containerRef = React.useRef<HTMLDivElement>(null);
  const mapInstanceRef = React.useRef<LeafletMapInstance | null>(null);

  React.useEffect(() => {
    let isMounted = true;

    async function init() {
      if (!containerRef.current || mapInstanceRef.current) return;

      const L = (await import("leaflet")).default;

      if (!isMounted || !containerRef.current) return;

      const map = L.map(containerRef.current).setView(center, zoom);

      // OpenStreetMap Tiles (free, no key needed)
      L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
        maxZoom: 19,
      }).addTo(map);

      const instance = new LeafletMapInstance(map, L);
      mapInstanceRef.current = instance;

      markers.forEach((m) => instance.addMarker(m));

      if (onMapReady) {
        onMapReady(instance);
      }
    }

    init();

    return () => {
      isMounted = false;
      if (mapInstanceRef.current) {
        mapInstanceRef.current.destroy();
        mapInstanceRef.current = null;
      }
    };
  }, []);

  // Update center when center prop changes
  React.useEffect(() => {
    if (mapInstanceRef.current) {
      mapInstanceRef.current.setCenter(center[0], center[1]);
    }
  }, [center[0], center[1]]);

  // Sync markers
  React.useEffect(() => {
    if (mapInstanceRef.current) {
      markers.forEach((m) => {
        mapInstanceRef.current?.updateMarker(m.id, m.position);
      });
    }
  }, [markers]);

  return (
    <div
      ref={containerRef}
      className={`relative z-0 border border-surface-border shadow-inner ${className}`}
    />
  );
}

