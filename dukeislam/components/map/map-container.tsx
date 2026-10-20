"use client";

import { useEffect, useMemo, useRef, useState, useCallback } from "react";
import { Map, Marker, Popup, setWorkerUrl } from "maplibre-gl";
import {
  Compass,
  Crosshair,
  MapPin,
  Navigation,
  Search,
  ShieldCheck,
  X,
  ZoomIn,
  ZoomOut,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";
import type {
  CampusBuildingProperties,
  EnrichedDiningVenue,
  NutritionInfo,
} from "@/lib/types";
import { campusBuildingsData } from "@/lib/map-data";
import { VenueMenuDrawer } from "./venue-menu-drawer";

if (typeof window !== "undefined") {
  try {
    setWorkerUrl("https://cdn.jsdelivr.net/npm/maplibre-gl@6.15.0/dist/maplibre-gl-worker.mjs");
  } catch {
    // fallback
  }
}

interface Props {
  venues: EnrichedDiningVenue[];
  nutrition: Record<string, NutritionInfo>;
}

// Campus Center Coordinates
const WEST_CAMPUS_CENTER: [number, number] = [-78.9395, 36.0010]; // [lng, lat]
const EAST_CAMPUS_CENTER: [number, number] = [-78.9139, 36.0076];

// Campus Alignment Presets:
// Bearing 30° aligns West Campus orthogonal to the viewport, making all basemap text ("Duke Chapel",
// "Page Auditorium", "Flowers Building", "Divinity School", "Chapel Dr") 100% horizontal and level towards the user view.
// Bearing -60° aligns Duke Chapel at the top ("North") looking down Abele Quad with orthogonal tiles.
const CAMPUS_GRID_BEARING = 30;
const CHAPEL_NORTH_BEARING = -60;
const CHAPEL_VIEW_CENTER: [number, number] = [-78.9398, 36.0013];
const CHAPEL_BEARING = 30;
const CHAPEL_PITCH = 0;

const DUKE_CAMPUS_BOUNDS: [[number, number], [number, number]] = [
  [-78.965, 35.985], // Southwest [lng, lat]
  [-78.895, 36.030], // Northeast [lng, lat]
];

interface CampusBuildingLabel {
  id: string;
  lines: string[];
  coords: [number, number]; // [lng, lat]
  rotation: number;
  baseSize: number;
  letterSpacing?: string;
  isBrodhead?: boolean;
}

// Vector typography for Brodhead Center focal dining building
// Aligned along Duke's West Campus quad grid angle (-31 degrees)
const CAMPUS_BUILDING_LABELS: CampusBuildingLabel[] = [
  {
    id: "35",
    lines: ["RICHARD H.", "BRODHEAD CENTER"],
    coords: [-78.93945, 36.00078],
    rotation: -31,
    baseSize: 14,
    letterSpacing: "0.18em",
    isBrodhead: true,
  },
];

function parseVenueIds(raw: unknown): string[] {
  if (!raw) return [];
  if (Array.isArray(raw)) return raw.map(String);
  if (typeof raw === "string") {
    const trimmed = raw.trim();
    if (trimmed.startsWith("[") && trimmed.endsWith("]")) {
      try {
        const parsed = JSON.parse(trimmed);
        if (Array.isArray(parsed)) return parsed.map(String);
      } catch {
        // fallback
      }
    }
    return trimmed.split(",").map((s) => s.trim()).filter(Boolean);
  }
  return [];
}

function getVenueIconSvg(venue: EnrichedDiningVenue): string {
  const c = venue.cuisine.toLowerCase();
  const id = venue.id.toLowerCase();
  if (c.includes("asian") || c.includes("noodle") || id.includes("ginger")) {
    return `<svg class="size-3 text-amber-200" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M12 21a9 9 0 0 0 9-9H3a9 9 0 0 0 9 9Z"/><path d="M7 12V7"/><path d="M12 12V4"/><path d="M17 12V8"/></svg>`;
  }
  if (c.includes("indian") || c.includes("curry") || id.includes("tandoor")) {
    return `<svg class="size-3 text-amber-300" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M8.5 14.5A2.5 2.5 0 0 0 11 12c0-1.38-.5-2-1-3-1.072-2.143-.224-4.054 2-6 .5 2.5 2 4.9 4 6.5 2 1.6 3 3.5 3 5.5a7 7 0 1 1-14 0c0-1.153.433-2.294 1-3a2.5 2.5 0 0 0 2.5 2.5z"/></svg>`;
  }
  if (c.includes("pizza") || c.includes("italian") || id.includes("forno")) {
    return `<svg class="size-3 text-red-300" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M15 11h.01"/><path d="M11 15h.01"/><path d="M16 16h.01"/><path d="m2 16 20 6-6-20A20 20 0 0 0 2 16Z"/></svg>`;
  }
  if (c.includes("coffee") || c.includes("bakery") || c.includes("espresso") || id.includes("perk") || id.includes("cafe")) {
    return `<svg class="size-3 text-amber-100" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M10 2v2"/><path d="M14 2v2"/><path d="M16 8a1 1 0 0 1 1 1v8a4 4 0 0 1-4 4H7a4 4 0 0 1-4-4V9a1 1 0 0 1 1-1h12Z"/><path d="M6 2v2"/><path d="M17 10h1a3 3 0 0 1 0 6h-1"/></svg>`;
  }
  if (c.includes("sushi") || c.includes("japanese") || id.includes("gyotaku")) {
    return `<svg class="size-3 text-cyan-200" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M6.5 12c.94-3.46 4.94-6 8.5-6 3.56 0 6.06 2.54 7 6-.94 3.47-3.44 6-7 6s-7.56-2.53-8.5-6Z"/><path d="M18 12v.5"/><path d="M16 17.93a7 7 0 0 1 0-11.86"/></svg>`;
  }
  if (c.includes("latin") || c.includes("mexican") || id.includes("sazon")) {
    return `<svg class="size-3 text-orange-300" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2a4 4 0 0 0-4 4c0 3.5 2 6 2 9a6 6 0 1 0 8-5.6V6a4 4 0 0 0-4-4z"/><path d="M14 6h-4"/></svg>`;
  }
  if (c.includes("plant") || c.includes("vegan") || id.includes("sprout") || id.includes("farmstead")) {
    return `<svg class="size-3 text-emerald-300" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M11 20A7 7 0 0 1 9.8 6.1C15.5 5 17 4.48 19 2c1 2 2 4.18 2 8 0 5.5-4.78 10-10 10Z"/><path d="M2 21c0-3 1.85-5.36 5.08-6C9.5 14.52 12 13 13 12"/></svg>`;
  }
  // Default Utensils
  return `<svg class="size-3 text-white" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M18 2v6a3 3 0 0 1-3 3 3 3 0 0 1-3-3V2"/><path d="M12 2v20"/><path d="m15 11 3 11"/><path d="M6 2v7a2 2 0 0 0 2 2h0a2 2 0 0 0 2-2V2"/><path d="M8 11v11"/></svg>`;
}

export function MapContainer({ venues, nutrition }: Props) {
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<Map | null>(null);
  const markersRef = useRef<Marker[]>([]);
  const buildingLabelMarkersRef = useRef<Marker[]>([]);
  const buildingLabelElementsRef = useRef<HTMLElement[]>([]);
  const userMarkerRef = useRef<Marker | null>(null);
  const hoverPopupRef = useRef<Popup | null>(null);

  // Filter States
  const [halalOnly, setHalalOnly] = useState(true);
  const [openOnly, setOpenOnly] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedCampus, setSelectedCampus] = useState<"All" | "West" | "East">("West");
  const [isClustered, setIsClustered] = useState(false);
  const [selectedVenue, setSelectedVenue] = useState<EnrichedDiningVenue | null>(null);
  const [locating, setLocating] = useState(false);
  const [locationToast, setLocationToast] = useState<string | null>(null);
  const [orientationMode, setOrientationMode] = useState<"standard" | "aligned" | "chapel-north">("standard");

  // Filtered venues list based on user controls
  const filteredVenues = useMemo(() => {
    return venues.filter((v) => {
      if (halalOnly && !v.isHalalCertified) return false;
      if (openOnly && v.isOpen !== true) return false;
      if (selectedCampus !== "All" && v.campus !== selectedCampus) return false;
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase().trim();
        const matchName = v.name.toLowerCase().includes(q);
        const matchCuisine = v.cuisine.toLowerCase().includes(q);
        const matchBuilding = v.building.toLowerCase().includes(q);
        const matchNotes = v.halalNotes?.toLowerCase().includes(q);
        const matchMenu = v.liveRestaurant?.categories.some((c) =>
          c.items.some((i) => i.name.toLowerCase().includes(q))
        );
        if (!matchName && !matchCuisine && !matchBuilding && !matchNotes && !matchMenu) {
          return false;
        }
      }
      return true;
    });
  }, [venues, halalOnly, openOnly, selectedCampus, searchQuery]);

  // Quick counts
  const halalCount = useMemo(() => venues.filter((v) => v.isHalalCertified).length, [venues]);
  const openCount = useMemo(
    () => venues.filter((v) => (halalOnly ? v.isHalalCertified : true) && v.isOpen === true).length,
    [venues, halalOnly]
  );

  // Initialize MapLibre GL
  useEffect(() => {
    if (!mapContainerRef.current || mapRef.current) return;

    const map = new Map({
      container: mapContainerRef.current,
      style: {
        version: 8,
        sources: {
          esri: {
            type: "raster",
            tiles: [
              "https://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile/{z}/{y}/{x}",
            ],
            tileSize: 256,
            maxzoom: 19, // Native max zoom of Esri Street Map - prevents "Map data not available"
            attribution: '&copy; Esri · Duke GIS',
          },
          buildings: {
            type: "geojson",
            data: campusBuildingsData as unknown as GeoJSON.GeoJSON,
            promoteId: "id",
          },
        },
        layers: [
          {
            id: "esri-basemap",
            type: "raster",
            source: "esri",
            minzoom: 0,
            maxzoom: 22,
          },
          {
            id: "building-fills",
            type: "fill",
            source: "buildings",
            paint: {
              "fill-color": ["get", "fillColor"],
              // Brodhead Center gets solid navy fill to host the central dining hall typography.
              // Other buildings remain transparent so their basemap labels are pristine and never severed.
              "fill-opacity": [
                "case",
                ["boolean", ["get", "isFocus"], false],
                1.0,
                0.0,
              ],
            },
          },
          {
            id: "building-strokes",
            type: "line",
            source: "buildings",
            paint: {
              "line-color": "#c82d30",
              "line-width": 2.5,
              // Only Brodhead Center gets the red focal boundary.
              // Other buildings have line-opacity 0.0 so no outlines slice across Flowers Building, Page Auditorium, etc.
              "line-opacity": [
                "case",
                ["boolean", ["get", "isFocus"], false],
                0.95,
                0.0,
              ],
            },
          },
        ],
      },
      center: WEST_CAMPUS_CENTER,
      zoom: 17.2,
      minZoom: 14.2,
      maxZoom: 20, // Clean overzoom without missing tile artifacts
      pitch: 25,
      bearing: -15,
      maxBounds: DUKE_CAMPUS_BOUNDS,
      attributionControl: false,
    });

    mapRef.current = map;
    if (typeof window !== "undefined") {
      (window as unknown as { mapInstance: Map }).mapInstance = map;
    }

    // Initialize architectural vector typography for colored campus buildings
    for (const b of CAMPUS_BUILDING_LABELS) {
      const containerEl = document.createElement("div");
      containerEl.className = "pointer-events-none select-none text-center z-0";

      const innerEl = document.createElement("div");
      innerEl.className = "pointer-events-none select-none text-center whitespace-nowrap will-change-transform";

      if (b.isBrodhead) {
        // Brodhead Center: clean architectural lettering without "Campus life"
        innerEl.innerHTML = `
          <div style="font-size: 11px; font-weight: 600; letter-spacing: 0.22em; color: rgba(255, 255, 255, 0.65); text-transform: uppercase; line-height: 1.1;">
            Richard H.
          </div>
          <div style="font-size: 15px; font-weight: 800; letter-spacing: 0.18em; color: rgba(255, 255, 255, 0.85); text-transform: uppercase; margin-top: 2px; line-height: 1.1;">
            Brodhead Center
          </div>
        `;
      } else if (b.lines.length === 2) {
        innerEl.innerHTML = `
          <div style="font-size: 10px; font-weight: 600; letter-spacing: 0.18em; color: rgba(255, 255, 255, 0.65); text-transform: uppercase; line-height: 1.1;">
            ${b.lines[0]}
          </div>
          <div style="font-size: ${b.baseSize}px; font-weight: 800; letter-spacing: ${b.letterSpacing || '0.16em'}; color: rgba(255, 255, 255, 0.80); text-transform: uppercase; margin-top: 1px; line-height: 1.1;">
            ${b.lines[1]}
          </div>
        `;
      } else {
        innerEl.innerHTML = `
          <div style="font-size: ${b.baseSize}px; font-weight: 700; letter-spacing: ${b.letterSpacing || '0.16em'}; color: rgba(255, 255, 255, 0.78); text-transform: uppercase; line-height: 1.1;">
            ${b.lines[0]}
          </div>
        `;
      }

      containerEl.appendChild(innerEl);

      const marker = new Marker({
        element: containerEl,
        anchor: "center",
        rotationAlignment: "viewport",
        pitchAlignment: "viewport",
      })
        .setLngLat(b.coords)
        .addTo(map);

      buildingLabelMarkersRef.current.push(marker);
      buildingLabelElementsRef.current.push(innerEl);
    }

    // Dynamic zoom-based geographic scaling of building architectural labels
    const updateBuildingLabelScales = () => {
      const zoom = map.getZoom();
      const HIDE_THRESHOLD = 16.2;
      const FULL_THRESHOLD = 16.7;
      const BASE_ZOOM = 17.5;

      if (zoom < HIDE_THRESHOLD) {
        for (const el of buildingLabelElementsRef.current) {
          el.style.display = "none";
        }
        return;
      }

      // Proportional geographic scaling: 2^(zoom - BASE_ZOOM)
      // When zooming out: text scales down at exact rate as building footprint
      // Clamped between 0.35 and 1.25 so it never spills out or grows uncontrollably
      const rawScale = Math.pow(2, zoom - BASE_ZOOM);
      const scale = Math.min(Math.max(rawScale, 0.35), 1.25);

      // Smooth fade-in between zoom 16.2 and 16.7
      const opacity = Math.min(Math.max((zoom - HIDE_THRESHOLD) / (FULL_THRESHOLD - HIDE_THRESHOLD), 0), 1) * 0.85;

      for (const el of buildingLabelElementsRef.current) {
        el.style.display = "block";
        el.style.transform = `scale(${scale})`;
        el.style.opacity = `${opacity}`;
        el.style.transformOrigin = "center center";
      }
    };

    // Track cluster threshold & update label scales on every zoom frame
    map.on("zoom", () => {
      const z = map.getZoom();
      const nextClustered = z < 16.2;
      setIsClustered((prev) => (prev !== nextClustered ? nextClustered : prev));
      updateBuildingLabelScales();
    });
    map.on("render", updateBuildingLabelScales);

    // Track bearing to update campus orientation state
    map.on("rotate", () => {
      const b = map.getBearing();
      const diffAligned = Math.abs(((b - CAMPUS_GRID_BEARING + 180) % 360) - 180);
      const diffChapel = Math.abs(((b - CHAPEL_NORTH_BEARING + 180) % 360) - 180);
      if (diffAligned < 5) {
        setOrientationMode("aligned");
      } else if (diffChapel < 5) {
        setOrientationMode("chapel-north");
      } else if (Math.abs(b) < 5) {
        setOrientationMode("standard");
      }
    });

    updateBuildingLabelScales();

    // Hover interactions on campus buildings
    hoverPopupRef.current = new Popup({
      closeButton: false,
      closeOnClick: false,
      offset: 15,
      className: "duke-building-popup",
    });

    map.on("mousemove", "building-fills", (e) => {
      if (!e.features || e.features.length === 0) return;
      map.getCanvas().style.cursor = "pointer";

      const feature = e.features[0];
      const props = feature.properties as CampusBuildingProperties;

      const coordinates = e.lngLat;
      const vIds = parseVenueIds(props.venueIds);
      const venueCount = vIds.length;
      const halalTag = props.hasHalal
        ? '<span class="inline-flex items-center rounded bg-emerald-600 px-1 py-0.2 text-[9px] font-bold text-white uppercase tracking-wider">HALAL</span>'
        : "";

      const html = `
        <div class="px-2.5 py-1.5 text-xs">
          <div class="flex items-center gap-1.5 font-bold text-foreground">
            <span>${props.shortName || props.name}</span>
            ${halalTag}
          </div>
          <div class="text-[11px] text-muted-foreground mt-0.5">
            ${venueCount > 0 ? `${venueCount} dining spots inside` : "Duke Campus Building"}
          </div>
        </div>
      `;

      hoverPopupRef.current?.setLngLat(coordinates).setHTML(html).addTo(map);
    });

    map.on("mouseleave", "building-fills", () => {
      map.getCanvas().style.cursor = "";
      hoverPopupRef.current?.remove();
    });

    // Clicking a building centers and zooms on it
    map.on("click", "building-fills", (e) => {
      if (!e.features || e.features.length === 0) return;
      const feature = e.features[0];
      const props = feature.properties as CampusBuildingProperties;

      map.flyTo({
        center: [e.lngLat.lng, e.lngLat.lat],
        zoom: Math.max(map.getZoom(), 17.8),
        pitch: 28,
        duration: 800,
      });

      // If building has exactly 1 venue, open it directly
      const vIds = parseVenueIds(props.venueIds);
      if (vIds.length === 1) {
        const found = venues.find((v) => v.id === vIds[0]);
        if (found) setSelectedVenue(found);
      }
    });

    // Empty canvas click clears selected venue
    map.on("click", (e) => {
      const features = map.queryRenderedFeatures(e.point, { layers: ["building-fills"] });
      if (features.length === 0) {
        setSelectedVenue(null);
      }
    });

    return () => {
      for (const m of buildingLabelMarkersRef.current) {
        m.remove();
      }
      buildingLabelMarkersRef.current = [];
      buildingLabelElementsRef.current = [];
      map.remove();
      mapRef.current = null;
    };
  }, [venues]);

  // Update HTML Markers with stable hit-tests (No hover:scale overlap glitching)
  const renderMarkers = useCallback(() => {
    const map = mapRef.current;
    if (!map) return;

    // Clear existing markers
    for (const m of markersRef.current) {
      m.remove();
    }
    markersRef.current = [];

    if (isClustered) {
      // Clustered Building Badges at lower zoom levels
      const buildingClusters = [
        {
          id: "35",
          name: "Brodhead Center",
          coords: [-78.939393, 36.000766] as [number, number],
          halalCount: 8,
          totalCount: 12,
          isFocus: true,
        },
        {
          id: "96",
          name: "Bryan Center",
          coords: [-78.941149, 36.001056] as [number, number],
          halalCount: 1,
          totalCount: 4,
          isFocus: false,
        },
        {
          id: "201",
          name: "Marketplace (East)",
          coords: [-78.913940, 36.007598] as [number, number],
          halalCount: 1,
          totalCount: 2,
          isFocus: false,
        },
        {
          id: "392",
          name: "The Perk (Perkins)",
          coords: [-78.938610, 36.002126] as [number, number],
          halalCount: 1,
          totalCount: 1,
          isFocus: false,
        },
        {
          id: "202",
          name: "Sanford Deli",
          coords: [-78.943927, 35.999400] as [number, number],
          halalCount: 1,
          totalCount: 1,
          isFocus: false,
        },
      ];

      for (const cluster of buildingClusters) {
        if (halalOnly && cluster.halalCount === 0) continue;

        const el = document.createElement("div");
        el.className = "cursor-pointer select-none";

        el.innerHTML = `
          <div class="flex items-center gap-1.5 rounded-full border-2 ${
            cluster.isFocus
              ? "border-[#c82d30] bg-[#001A57] text-white shadow-xl"
              : "border-primary/40 bg-[#1D3557] text-white shadow-md"
          } px-3 py-1.5 text-xs font-semibold hover:border-white transition-colors duration-150">
            <span>${cluster.name}</span>
            <span class="rounded bg-emerald-600 px-1.5 py-0.2 text-[10px] font-bold text-white uppercase tracking-wider">
              ${cluster.halalCount > 0 ? `${cluster.halalCount} Halal` : `${cluster.totalCount} Spots`}
            </span>
          </div>
        `;

        el.addEventListener("click", () => {
          map.flyTo({
            center: cluster.coords,
            zoom: 17.8,
            pitch: 28,
            duration: 800,
          });
          setIsClustered(false);
        });

        const marker = new Marker({ element: el })
          .setLngLat(cluster.coords)
          .addTo(map);

        markersRef.current.push(marker);
      }
      return;
    }

    // High Zoom: Render individual food stalls at micro-coordinates
    // Using official Duke Mobile Order icons for authentic campus branding
    for (const venue of filteredVenues) {
      const el = document.createElement("div");
      // Stable hit target: no hover:scale-110, no z-index thrashing
      el.className = "cursor-pointer select-none";

      const isHalal = venue.isHalalCertified;
      const iconHtml = venue.iconUrl
        ? `<img src="${venue.iconUrl}" alt="" class="size-4.5 shrink-0 rounded-full object-cover bg-white ring-1 ring-white/20" />`
        : `<span class="flex size-4.5 shrink-0 items-center justify-center rounded-full bg-white/15">${getVenueIconSvg(venue)}</span>`;

      const badgeStyle = isHalal
        ? "border-emerald-600/80 bg-[#001A57] text-white shadow-md hover:border-emerald-400 hover:shadow-lg"
        : "border-border/80 bg-[#1D3557] text-white shadow-sm hover:border-white";

      el.innerHTML = `
        <div class="flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-[11px] font-semibold transition-colors duration-150 ${badgeStyle}">
          ${iconHtml}
          <span class="max-w-[130px] truncate leading-tight">${venue.name}</span>
          ${
            isHalal
              ? `<span class="shrink-0 rounded bg-emerald-600 px-1 py-0.2 font-mono text-[9px] font-bold tracking-wider text-white uppercase">
                  HALAL
                 </span>`
              : ""
          }
        </div>
      `;

      el.addEventListener("click", (e) => {
        e.stopPropagation();
        setSelectedVenue(venue);
        map.flyTo({
          center: [venue.coordinates[1], venue.coordinates[0]],
          zoom: Math.max(map.getZoom(), 18),
          pitch: 28,
          duration: 600,
        });
      });

      const marker = new Marker({
        element: el,
        anchor: "center",
      })
        .setLngLat([venue.coordinates[1], venue.coordinates[0]])
        .addTo(map);

      markersRef.current.push(marker);
    }
  }, [filteredVenues, isClustered, halalOnly]);

  useEffect(() => {
    renderMarkers();
  }, [renderMarkers]);

  // Geolocation Handler ("Locate Me")
  const handleLocateMe = useCallback(() => {
    if (!navigator.geolocation) {
      setLocationToast("Geolocation is not supported by your browser.");
      return;
    }

    setLocating(true);
    setLocationToast(null);

    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setLocating(false);
        const { latitude, longitude } = pos.coords;
        const userLngLat: [number, number] = [longitude, latitude];

        const map = mapRef.current;
        if (!map) return;

        // User location beacon marker
        if (!userMarkerRef.current) {
          const el = document.createElement("div");
          el.className = "relative flex items-center justify-center";
          el.innerHTML = `
            <span class="absolute size-6 rounded-full bg-blue-500/30 animate-ping"></span>
            <span class="relative size-3.5 rounded-full border-2 border-white bg-blue-600 shadow-md"></span>
          `;
          userMarkerRef.current = new Marker({ element: el })
            .setLngLat(userLngLat)
            .addTo(map);
        } else {
          userMarkerRef.current.setLngLat(userLngLat);
        }

        const isNearDuke =
          latitude >= 35.98 &&
          latitude <= 36.03 &&
          longitude >= -78.965 &&
          longitude <= -78.895;

        if (isNearDuke) {
          map.flyTo({
            center: userLngLat,
            zoom: 17.5,
            pitch: 25,
            duration: 1200,
          });
          setLocationToast("Located on Duke campus!");
        } else {
          map.flyTo({
            center: WEST_CAMPUS_CENTER,
            zoom: 17.2,
            duration: 1200,
          });
          setLocationToast("You appear to be off-campus. Centering Duke West Campus.");
        }

        setTimeout(() => setLocationToast(null), 4000);
      },
      () => {
        setLocating(false);
        setLocationToast("Location access unavailable or denied.");
        setTimeout(() => setLocationToast(null), 4000);
      },
      { enableHighAccuracy: true, timeout: 8000 }
    );
  }, []);

  // Fly to campus presets
  const handleCampusSwitch = (campus: "All" | "West" | "East") => {
    setSelectedCampus(campus);
    const map = mapRef.current;
    if (!map) return;

    if (campus === "West") {
      map.flyTo({
        center: WEST_CAMPUS_CENTER,
        zoom: 17.4,
        pitch: 25,
        bearing: -15,
        duration: 900,
      });
    } else if (campus === "East") {
      map.flyTo({
        center: EAST_CAMPUS_CENTER,
        zoom: 17.2,
        pitch: 15,
        bearing: 0,
        duration: 900,
      });
    } else {
      map.fitBounds(DUKE_CAMPUS_BOUNDS, {
        padding: 50,
        duration: 900,
      });
    }
  };

  // Switch Campus Orientation Mode:
  // - "aligned": Bearing 30°, pitch 0 — text & buildings 100% horizontal to user view
  // - "chapel-north": Bearing -60°, pitch 0 — Duke Chapel at top (North) looking down Abele Quad
  // - "standard": Bearing 0°, pitch 25° — True North-Up
  const handleSetOrientation = useCallback((targetMode: "aligned" | "chapel-north") => {
    const map = mapRef.current;
    if (!map) return;

    if (orientationMode === targetMode) {
      // Toggle back to standard North-Up
      setOrientationMode("standard");
      map.flyTo({
        center: WEST_CAMPUS_CENTER,
        zoom: 17.4,
        bearing: 0,
        pitch: 25,
        duration: 900,
        essential: true,
      });
      setLocationToast("Reset to Standard North-Up orientation");
      setTimeout(() => setLocationToast(null), 3000);
      return;
    }

    setSelectedCampus("West");
    setOrientationMode(targetMode);

    if (targetMode === "aligned") {
      map.flyTo({
        center: CHAPEL_VIEW_CENTER,
        zoom: 17.5,
        bearing: CAMPUS_GRID_BEARING,
        pitch: 0,
        duration: 1000,
        essential: true,
      });
      setLocationToast("Aligned to Campus Grid (text & tiles level to your view)");
    } else {
      map.flyTo({
        center: CHAPEL_VIEW_CENTER,
        zoom: 17.5,
        bearing: CHAPEL_NORTH_BEARING,
        pitch: 0,
        duration: 1000,
        essential: true,
      });
      setLocationToast("Chapel Entrance: North (facing down Abele Quad)");
    }
    setTimeout(() => setLocationToast(null), 3000);
  }, [orientationMode]);

  return (
    <div className="relative h-[calc(100dvh-3.5rem)] w-full overflow-hidden bg-[#EAE8E3]">
      {/* Map Container Element */}
      <div ref={mapContainerRef} className="h-full w-full outline-hidden" />

      {/* Top Floating Controls & Filter Bar (Clean, unblurred, minimal) */}
      <div className="pointer-events-none absolute inset-x-0 top-3 z-20 flex flex-col items-center gap-2 px-3 sm:px-6">
        {/* Search & Main Switchers Card */}
        <div className="pointer-events-auto flex w-full max-w-2xl flex-col gap-2 rounded-2xl border border-border/70 bg-background/95 p-2 shadow-lg sm:flex-row sm:items-center sm:gap-3 sm:p-2.5">
          {/* Search Box */}
          <div className="relative flex-1">
            <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search halal dishes, spots, or buildings…"
              className="h-9.5 rounded-xl bg-card pl-9 pr-8 text-xs sm:text-sm shadow-none border-border/70"
            />
            {searchQuery && (
              <button
                type="button"
                onClick={() => setSearchQuery("")}
                className="absolute right-2.5 top-1/2 -translate-y-1/2 rounded-full p-1 text-muted-foreground hover:bg-muted"
                aria-label="Clear search"
              >
                <X className="size-3.5" />
              </button>
            )}
          </div>

          {/* Campus Quick Switcher Pills */}
          <div className="flex shrink-0 items-center justify-between gap-1 border-t border-border/40 pt-1.5 sm:border-t-0 sm:pt-0">
            <div className="flex items-center gap-1 rounded-xl bg-muted/60 p-1">
              {(["West", "East", "All"] as const).map((campus) => (
                <button
                  key={campus}
                  type="button"
                  onClick={() => handleCampusSwitch(campus)}
                  className={cn(
                    "rounded-lg px-2.5 py-1 text-xs font-semibold transition-all active:scale-95",
                    selectedCampus === campus
                      ? "bg-primary text-primary-foreground shadow-xs"
                      : "text-muted-foreground hover:text-foreground"
                  )}
                >
                  {campus === "All" ? "All Campus" : `${campus} Campus`}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Quick Filter Badges */}
        <div className="pointer-events-auto flex w-full max-w-3xl items-center gap-2 overflow-x-auto px-1 pb-1 [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
          <button
            type="button"
            onClick={() => setHalalOnly((v) => !v)}
            className={cn(
              "flex shrink-0 items-center gap-1.5 rounded-full border px-3 py-1.5 text-xs font-semibold shadow-xs transition-all active:scale-95",
              halalOnly
                ? "border-emerald-600 bg-emerald-600 text-white"
                : "border-border/80 bg-background/95 text-muted-foreground hover:border-foreground/30 hover:text-foreground"
            )}
          >
            <ShieldCheck className="size-3.5" />
            <span>Halal Only</span>
            <span
              className={cn(
                "rounded-full px-1.5 py-0.2 text-[10px] font-bold",
                halalOnly ? "bg-emerald-700 text-white" : "bg-muted text-muted-foreground"
              )}
            >
              {halalCount}
            </span>
          </button>

          <button
            type="button"
            onClick={() => setOpenOnly((v) => !v)}
            className={cn(
              "flex shrink-0 items-center gap-1.5 rounded-full border px-3 py-1.5 text-xs font-semibold shadow-xs transition-all active:scale-95",
              openOnly
                ? "border-primary bg-primary text-primary-foreground"
                : "border-border/80 bg-background/95 text-muted-foreground hover:border-foreground/30 hover:text-foreground"
            )}
          >
            <span
              className={cn(
                "size-1.5 rounded-full",
                openOnly ? "bg-white" : "bg-emerald-500"
              )}
            />
            <span>Open Now</span>
            <span
              className={cn(
                "rounded-full px-1.5 py-0.2 text-[10px] font-bold",
                openOnly ? "bg-primary-foreground/20 text-white" : "bg-muted text-muted-foreground"
              )}
            >
              {openCount}
            </span>
          </button>

          {/* Direct shortcut to Brodhead Center */}
          <button
            type="button"
            onClick={() => {
              setSelectedCampus("West");
              setIsClustered(false);
              mapRef.current?.flyTo({
                center: WEST_CAMPUS_CENTER,
                zoom: 18.2,
                pitch: 28,
                duration: 800,
              });
            }}
            className="flex shrink-0 items-center gap-1 rounded-full border border-border/80 bg-background/95 px-3 py-1.5 text-xs font-medium text-foreground shadow-xs hover:bg-accent active:scale-95"
          >
            <MapPin className="size-3 text-[#001A57] dark:text-blue-400" />
            <span>Brodhead Center Stalls</span>
          </button>

          {/* Campus Grid Horizontal View Toggle (Level Text & Buildings) */}
          <button
            type="button"
            onClick={() => handleSetOrientation("aligned")}
            className={cn(
              "flex shrink-0 items-center gap-1.5 rounded-full border px-3 py-1.5 text-xs font-medium shadow-xs transition-all active:scale-95",
              orientationMode === "aligned"
                ? "border-[#001A57] bg-[#001A57] text-white shadow-sm font-semibold"
                : "border-border/80 bg-background/95 text-foreground hover:bg-accent"
            )}
            title="Align map to campus grid: text and buildings are horizontal to your view"
          >
            <Compass className={cn("size-3.5 transition-transform duration-300", orientationMode === "aligned" ? "text-amber-300 rotate-45" : "text-primary")} />
            <span>{orientationMode === "aligned" ? "Campus: Level" : "Align Campus"}</span>
          </button>

          {/* Chapel North View Toggle (Duke Chapel at North / top of screen) */}
          <button
            type="button"
            onClick={() => handleSetOrientation("chapel-north")}
            className={cn(
              "flex shrink-0 items-center gap-1.5 rounded-full border px-3 py-1.5 text-xs font-medium shadow-xs transition-all active:scale-95",
              orientationMode === "chapel-north"
                ? "border-[#001A57] bg-[#001A57] text-white shadow-sm font-semibold"
                : "border-border/80 bg-background/95 text-foreground hover:bg-accent"
            )}
            title="Orient map with Duke Chapel entrance at the top (North) looking down Abele Quad"
          >
            <Navigation className={cn("size-3.5 transition-transform duration-300", orientationMode === "chapel-north" ? "-rotate-90 text-amber-300" : "text-primary")} />
            <span>{orientationMode === "chapel-north" ? "Chapel: North" : "Chapel North"}</span>
          </button>

          {/* Results count pill */}
          <span className="ml-auto shrink-0 text-[11px] font-medium text-muted-foreground bg-background/85 px-2.5 py-1 rounded-full border border-border/50">
            {filteredVenues.length} {filteredVenues.length === 1 ? "spot" : "spots"} found
          </span>
        </div>
      </div>

      {/* Location Status Toast Message */}
      {locationToast && (
        <div className="pointer-events-none absolute bottom-20 inset-x-0 z-30 flex justify-center px-4 animate-in fade-in slide-in-from-bottom-2 duration-300">
          <div className="pointer-events-auto rounded-xl border border-primary/20 bg-background/95 px-4 py-2 text-xs font-medium shadow-lg text-foreground">
            {locationToast}
          </div>
        </div>
      )}

      {/* Floating Map Actions (Bottom-Right) */}
      <div className="pointer-events-none absolute bottom-6 right-4 z-20 flex flex-col gap-2">
        {/* Locate Me Button */}
        <Button
          type="button"
          size="icon"
          variant="secondary"
          onClick={handleLocateMe}
          disabled={locating}
          className="pointer-events-auto size-11 rounded-2xl border border-border/70 bg-background/95 shadow-lg hover:bg-accent active:scale-95"
          aria-label="Locate me on campus"
        >
          <Crosshair className={cn("size-5 text-primary", locating && "animate-spin")} />
        </Button>

        {/* Cycle Campus Alignment (Aligned -> Chapel North -> Standard) */}
        <Button
          type="button"
          size="icon"
          variant={orientationMode !== "standard" ? "default" : "secondary"}
          onClick={() => {
            if (orientationMode === "standard") {
              handleSetOrientation("aligned");
            } else if (orientationMode === "aligned") {
              handleSetOrientation("chapel-north");
            } else {
              handleSetOrientation("chapel-north"); // toggles back to standard
            }
          }}
          className={cn(
            "pointer-events-auto size-11 rounded-2xl border shadow-lg active:scale-95 transition-all",
            orientationMode !== "standard"
              ? "border-[#001A57] bg-[#001A57] text-white hover:bg-[#001A57]/90"
              : "border-border/70 bg-background/95 text-foreground hover:bg-accent"
          )}
          aria-label="Toggle Campus Orientation"
          title={
            orientationMode === "standard"
              ? "Click to align campus grid (level text & buildings)"
              : orientationMode === "aligned"
              ? "Click to orient Chapel entrance North"
              : "Click to reset to Standard North-Up"
          }
        >
          <Navigation
            className={cn(
              "size-5 transition-transform duration-300",
              orientationMode === "aligned"
                ? "rotate-45 text-amber-300"
                : orientationMode === "chapel-north"
                ? "-rotate-90 text-amber-300"
                : "text-primary"
            )}
          />
        </Button>

        {/* Recenter West Campus */}
        <Button
          type="button"
          size="icon"
          variant="secondary"
          onClick={() => {
            mapRef.current?.flyTo({
              center: WEST_CAMPUS_CENTER,
              zoom: 17.4,
              pitch: 25,
              bearing: -15,
              duration: 800,
            });
          }}
          className="pointer-events-auto size-11 rounded-2xl border border-border/70 bg-background/95 shadow-lg hover:bg-accent active:scale-95"
          aria-label="Recenter campus"
        >
          <Compass className="size-5 text-foreground" />
        </Button>

        {/* Zoom Controls */}
        <div className="pointer-events-auto flex flex-col overflow-hidden rounded-2xl border border-border/70 bg-background/95 shadow-lg">
          <button
            type="button"
            onClick={() => mapRef.current?.zoomIn()}
            className="flex size-11 items-center justify-center text-foreground hover:bg-accent active:bg-muted"
            aria-label="Zoom in"
          >
            <ZoomIn className="size-4.5" />
          </button>
          <div className="h-px bg-border/60" />
          <button
            type="button"
            onClick={() => mapRef.current?.zoomOut()}
            className="flex size-11 items-center justify-center text-foreground hover:bg-accent active:bg-muted"
            aria-label="Zoom out"
          >
            <ZoomOut className="size-4.5" />
          </button>
        </div>
      </div>

      {/* Floating Legend Pill (Bottom-Left) */}
      <div className="pointer-events-none absolute bottom-6 left-4 z-20 hidden sm:flex items-center gap-2 rounded-xl border border-border/60 bg-background/90 px-3 py-1.5 text-[11px] font-medium shadow-md text-foreground">
        <span className="flex items-center gap-1">
          <span className="rounded bg-emerald-600 px-1 py-0.2 font-mono text-[9px] font-bold text-white uppercase">HALAL</span>
          <span>Verified Options</span>
        </span>
        <span className="text-border">|</span>
        <span className="flex items-center gap-1.5">
          <span className="size-2.5 rounded-sm bg-[#001A57] border border-[#c82d30]"></span>
          <span>Brodhead Center</span>
        </span>
        <span className="text-border">|</span>
        <span className="text-muted-foreground">Tap building or pin for menu</span>
      </div>

      {/* Bottom Sheet / Drawer for Selected Venue */}
      <VenueMenuDrawer
        venue={selectedVenue}
        open={selectedVenue !== null}
        onOpenChange={(open) => !open && setSelectedVenue(null)}
        nutrition={nutrition}
      />
    </div>
  );
}
