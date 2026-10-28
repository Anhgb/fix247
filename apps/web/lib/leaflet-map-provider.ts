"use client";

import type { MapInstance, MapMarker, MapOptions, MapProvider } from "./map-provider";

export class LeafletMapInstance implements MapInstance {
  private map: any;
  private markers: Map<string, any> = new Map();
  private L: any;

  constructor(map: any, L: any) {
    this.map = map;
    this.L = L;
  }

  setCenter(lat: number, lng: number): void {
    if (this.map) {
      this.map.panTo([lat, lng]);
    }
  }

  addMarker(marker: MapMarker): void {
    if (!this.map || !this.L) return;

    // Custom icons
    let iconHtml = "📍";
    if (marker.icon === "technician") {
      iconHtml = "🛵";
    } else if (marker.icon === "customer") {
      iconHtml = "🏠";
    }

    const divIcon = this.L.divIcon({
      html: `<div style="font-size: 26px; line-height: 1; filter: drop-shadow(0 2px 4px rgba(0,0,0,0.5));">${iconHtml}</div>`,
      className: "custom-leaflet-marker",
      iconSize: [30, 30],
      iconAnchor: [15, 15],
    });

    const lMarker = this.L.marker(marker.position, { icon: divIcon }).addTo(this.map);
    if (marker.popup) {
      lMarker.bindPopup(marker.popup);
    }
    this.markers.set(marker.id, lMarker);
  }

  updateMarker(id: string, position: [number, number]): void {
    const lMarker = this.markers.get(id);
    if (lMarker) {
      lMarker.setLatLng(position);
    }
  }

  removeMarker(id: string): void {
    const lMarker = this.markers.get(id);
    if (lMarker) {
      lMarker.remove();
      this.markers.delete(id);
    }
  }

  destroy(): void {
    if (this.map) {
      this.map.remove();
      this.map = null;
    }
    this.markers.clear();
  }
}

export const defaultMapProvider: MapProvider = {
  createMap(container: HTMLElement, options: MapOptions): MapInstance {
    throw new Error("Use LeafletMap React component for dynamic loading in Next.js");
  },
};
