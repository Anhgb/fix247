/**
 * MapProvider Interface – Fix 24/7 (A-05, D-10)
 * Pluggable map architecture: default is Leaflet / OpenStreetMap (free, no API key).
 * Google Maps or Goong can be plugged in later by implementing MapProvider.
 */

export interface MapOptions {
  center: [number, number]; // [lat, lng]
  zoom: number;
}

export interface MapMarker {
  id: string;
  position: [number, number];
  icon?: "technician" | "customer" | "default";
  popup?: string;
}

export interface MapInstance {
  setCenter(lat: number, lng: number): void;
  addMarker(marker: MapMarker): void;
  updateMarker(id: string, position: [number, number]): void;
  removeMarker(id: string): void;
  destroy(): void;
}

export interface MapProvider {
  createMap(container: HTMLElement, options: MapOptions): MapInstance;
}
