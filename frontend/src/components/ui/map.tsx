import React, { createContext, useContext, useEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import * as maplibregl from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';

interface MapContextType {
  map: maplibregl.Map | null;
  loaded: boolean;
}

const MapContext = createContext<MapContextType>({ map: null, loaded: false });

export const useMap = () => useContext(MapContext);

// Highly reliable dark map raster style (CartoDB Dark Matter tiles)
const defaultDarkStyle: maplibregl.StyleSpecification = {
  version: 8,
  sources: {
    'carto-dark': {
      type: 'raster',
      tiles: [
        'https://a.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}@2x.png',
        'https://b.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}@2x.png',
        'https://c.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}@2x.png',
        'https://d.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}@2x.png',
      ],
      tileSize: 256,
      attribution: '&copy; OpenStreetMap &copy; CARTO',
    },
  },
  layers: [
    {
      id: 'carto-dark-layer',
      type: 'raster',
      source: 'carto-dark',
      minzoom: 0,
      maxzoom: 22,
    },
  ],
};

interface MapProps {
  center?: [number, number];
  zoom?: number;
  mapStyle?: string | maplibregl.StyleSpecification;
  className?: string;
  children?: React.ReactNode;
}

export const Map: React.FC<MapProps> = ({
  center = [-73.98, 40.75],
  zoom = 11.2,
  mapStyle = defaultDarkStyle,
  className = 'h-[450px] w-full rounded-lg overflow-hidden',
  children,
}) => {
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const [map, setMap] = useState<maplibregl.Map | null>(null);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    if (!mapContainerRef.current) return;

    const mapInstance = new maplibregl.Map({
      container: mapContainerRef.current,
      style: mapStyle,
      center: center,
      zoom: zoom,
      attributionControl: false,
    });

    mapInstance.addControl(new maplibregl.NavigationControl({ showCompass: false }), 'bottom-right');

    const handleLoad = () => {
      setLoaded(true);
      mapInstance.resize();
    };

    if (mapInstance.loaded()) {
      handleLoad();
    } else {
      mapInstance.on('load', handleLoad);
    }

    // ResizeObserver ensures canvas updates bounds when container scales or toggles visibility
    const resizeObserver = new ResizeObserver(() => {
      mapInstance.resize();
    });
    resizeObserver.observe(mapContainerRef.current);

    setMap(mapInstance);

    return () => {
      resizeObserver.disconnect();
      mapInstance.remove();
    };
  }, []);

  return (
    <div className={`relative ${className}`}>
      {/* Absolute canvas container element for MapLibre GL */}
      <div ref={mapContainerRef} className="absolute inset-0 w-full h-full rounded-lg overflow-hidden bg-[#101010]" />
      
      {/* React context and children overlay */}
      <MapContext.Provider value={{ map, loaded }}>
        {loaded && children}
      </MapContext.Provider>
    </div>
  );
};

interface MapRouteProps {
  coordinates: [number, number][];
  color?: string;
  width?: number;
  opacity?: number;
}

export const MapRoute: React.FC<MapRouteProps> = ({
  coordinates,
  color = '#3b82f6',
  width = 4,
  opacity = 0.8,
}) => {
  const { map, loaded } = useMap();
  const routeIdRef = useRef(`route-${Math.random().toString(36).substr(2, 9)}`);

  useEffect(() => {
    if (!map || !loaded) return;

    const sourceId = `source-${routeIdRef.current}`;
    const layerId = `layer-${routeIdRef.current}`;

    const geojson: GeoJSON.Feature<GeoJSON.LineString> = {
      type: 'Feature',
      properties: {},
      geometry: {
        type: 'LineString',
        coordinates: coordinates,
      },
    };

    if (map.getSource(sourceId)) {
      (map.getSource(sourceId) as maplibregl.GeoJSONSource).setData(geojson);
    } else {
      map.addSource(sourceId, {
        type: 'geojson',
        data: geojson,
      });

      map.addLayer({
        id: layerId,
        type: 'line',
        source: sourceId,
        layout: {
          'line-join': 'round',
          'line-cap': 'round',
        },
        paint: {
          'line-color': color,
          'line-width': width,
          'line-opacity': opacity,
        },
      });
    }

    return () => {
      if (map.getLayer(layerId)) {
        map.removeLayer(layerId);
      }
      if (map.getSource(sourceId)) {
        map.removeSource(sourceId);
      }
    };
  }, [map, loaded, coordinates, color, width, opacity]);

  return null;
};

interface MapMarkerProps {
  longitude: number;
  latitude: number;
  children?: React.ReactNode;
}

export const MapMarkerContext = createContext<{
  marker: maplibregl.Marker | null;
  markerElement: HTMLDivElement | null;
}>({ marker: null, markerElement: null });

export const MapMarker: React.FC<MapMarkerProps> = ({
  longitude,
  latitude,
  children,
}) => {
  const { map, loaded } = useMap();
  const [marker, setMarker] = useState<maplibregl.Marker | null>(null);
  const elementRef = useRef<HTMLDivElement>(document.createElement('div'));

  useEffect(() => {
    if (!map || !loaded) return;

    const el = elementRef.current;
    el.className = 'map-marker-container cursor-pointer z-10';

    const newMarker = new maplibregl.Marker({ element: el })
      .setLngLat([longitude, latitude])
      .addTo(map);

    setMarker(newMarker);

    return () => {
      newMarker.remove();
    };
  }, [map, loaded, longitude, latitude]);

  return (
    <MapMarkerContext.Provider value={{ marker, markerElement: elementRef.current }}>
      {children}
    </MapMarkerContext.Provider>
  );
};

export const MarkerContent: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { markerElement } = useContext(MapMarkerContext);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    if (markerElement) {
      setMounted(true);
    }
  }, [markerElement]);

  if (!markerElement || !mounted) return null;

  return createPortal(children, markerElement);
};

export const MarkerTooltip: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { markerElement } = useContext(MapMarkerContext);
  const [isHovered, setIsHovered] = useState(false);

  useEffect(() => {
    if (!markerElement) return;

    const handleMouseEnter = () => setIsHovered(true);
    const handleMouseLeave = () => setIsHovered(false);

    markerElement.addEventListener('mouseenter', handleMouseEnter);
    markerElement.addEventListener('mouseleave', handleMouseLeave);

    return () => {
      markerElement.removeEventListener('mouseenter', handleMouseEnter);
      markerElement.removeEventListener('mouseleave', handleMouseLeave);
    };
  }, [markerElement]);

  if (!isHovered) return null;

  return (
    <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-2.5 py-1 bg-black/90 text-white text-xs rounded whitespace-nowrap z-50 pointer-events-none border border-[#333] shadow-lg">
      {children}
    </div>
  );
};

export const MarkerPopup: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { map } = useMap();
  const { marker, markerElement } = useContext(MapMarkerContext);
  const [popupNode] = useState(() => document.createElement('div'));

  useEffect(() => {
    if (!map || !markerElement) return;

    const popup = new maplibregl.Popup({
      closeButton: false,
      closeOnClick: true,
      offset: 15,
      className: 'maplibre-custom-popup',
    }).setDOMContent(popupNode);

    const handleMarkerClick = (e: MouseEvent) => {
      e.stopPropagation();
      if (popup.isOpen()) {
        popup.remove();
      } else if (marker) {
        popup.setLngLat(marker.getLngLat()).addTo(map);
      }
    };

    markerElement.addEventListener('click', handleMarkerClick);

    return () => {
      markerElement.removeEventListener('click', handleMarkerClick);
      if (popup.isOpen()) {
        popup.remove();
      }
    };
  }, [map, marker, markerElement, popupNode]);

  return createPortal(children, popupNode);
};

export interface HeatmapPoint {
  lng: number;
  lat: number;
  weight?: number;
}

export interface MapHeatmapProps {
  data: HeatmapPoint[];
  radius?: number;
  opacity?: number;
  intensity?: number;
}

export const MapHeatmap: React.FC<MapHeatmapProps> = ({
  data,
  radius = 35,
  opacity = 0.85,
  intensity = 1.2,
}) => {
  const { map, loaded } = useMap();
  const heatmapIdRef = useRef(`heatmap-${Math.random().toString(36).substr(2, 9)}`);

  useEffect(() => {
    if (!map || !loaded) return;

    const sourceId = `source-${heatmapIdRef.current}`;
    const layerId = `layer-${heatmapIdRef.current}`;

    const geojson: GeoJSON.FeatureCollection<GeoJSON.Point> = {
      type: 'FeatureCollection',
      features: data.map((pt) => ({
        type: 'Feature',
        properties: {
          weight: pt.weight ?? 1,
        },
        geometry: {
          type: 'Point',
          coordinates: [pt.lng, pt.lat],
        },
      })),
    };

    if (map.getSource(sourceId)) {
      (map.getSource(sourceId) as maplibregl.GeoJSONSource).setData(geojson);
    } else {
      map.addSource(sourceId, {
        type: 'geojson',
        data: geojson,
      });

      map.addLayer({
        id: layerId,
        type: 'heatmap',
        source: sourceId,
        maxzoom: 15,
        paint: {
          'heatmap-weight': ['get', 'weight'],
          'heatmap-intensity': intensity,
          'heatmap-color': [
            'interpolate',
            ['linear'],
            ['heatmap-density'],
            0, 'rgba(0,0,255,0)',
            0.2, 'rgb(0,255,255)',
            0.4, 'rgb(0,255,0)',
            0.6, 'rgb(255,255,0)',
            0.8, 'rgb(255,165,0)',
            1, 'rgb(255,0,0)',
          ],
          'heatmap-radius': radius,
          'heatmap-opacity': opacity,
        },
      });
    }

    return () => {
      if (map.getLayer(layerId)) {
        map.removeLayer(layerId);
      }
      if (map.getSource(sourceId)) {
        map.removeSource(sourceId);
      }
    };
  }, [map, loaded, data, radius, opacity, intensity]);

  return null;
};
