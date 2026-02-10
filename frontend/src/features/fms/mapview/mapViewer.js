import { useMap, MapContainer, Polyline, Marker, Popup } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import { useState, useEffect, useRef, useMemo } from 'react';
import L from 'leaflet'

delete L.Icon.Default.prototype._getIconUrl;

L.Icon.Default.mergeOptions({
    iconRetinaUrl: require('leaflet/dist/images/marker-icon-2x.png'),
    iconUrl: require('leaflet/dist/images/marker-icon.png'),
    shadowUrl: require('leaflet/dist/images/marker-shadow.png'),
    iconSize:[20, 30]
});

const createSvgIcon = (svgHtml, size, anchorY) => {
    return L.divIcon({
        html: svgHtml,
        className: '',
        iconSize: [size, size],
        iconAnchor: [Math.floor(size / 2), anchorY || size]
    })
}

const pinSvg = (size) => {
    const w = size;
    const h = size;
    return `
        <svg width="${w}" height="${h}" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
            <path d="M12 2C8.134 2 5 5.134 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.866-3.134-7-7-7zm0 9.5a2.5 2.5 0 1 1 0-5 2.5 2.5 0 0 1 0 5z" fill="#FFFFFF"/>
        </svg>
    `
}

const VehicleMarker = ({pose, text, type, zoom}) => {
    if (!pose || !pose.valid) return null;

    const baseSize = Math.max(18, Math.round(zoom * 1.1));

    if (type === 'current') {
        const sizeCurr = Math.max(35, Math.round(zoom * 2.5));
        const heading = (typeof pose.heading === 'number') ? pose.heading : 0;
        // Apply rotation with 180° offset to correct car image orientation
        const rotatedHeading = ((360 - heading + 180) % 360 + 360) % 360;
        
        const icon = L.divIcon({
            html: `
                <div style="
                    width: ${sizeCurr}px;
                    height: ${Math.floor(sizeCurr * 0.7)}px;
                    background-image: url('/white-car-icon.png');
                    background-size: contain;
                    background-repeat: no-repeat;
                    background-position: center;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    transform: rotate(${rotatedHeading}deg);
                    transform-origin: center center;
                "></div>
            `,
            className: 'vehicle-marker-current',
            iconSize: [sizeCurr, Math.floor(sizeCurr * 0.7)],
            iconAnchor: [Math.floor(sizeCurr / 2), Math.floor(sizeCurr * 0.35)],
            popupAnchor: [0, -Math.floor(sizeCurr * 0.35)]
        });
        return (
            <Marker position={pose} icon={icon}>
                <Popup>{text}</Popup>
            </Marker>
        )
    } else if (type === 'goal') {
        const icon = createSvgIcon(pinSvg(baseSize), baseSize, baseSize);
        return (
            <Marker position={pose} icon={icon}>
                <Popup>{text}</Popup>
            </Marker>
        )
    }

    // fallback - small white pin
    const icon = createSvgIcon(pinSvg(baseSize), baseSize, baseSize);
    return (
        <Marker position={pose} icon={icon}>
            <Popup>{text}</Popup>
        </Marker>
    )
}

const ShowCoordinates = () => {
    const map = useMap();
  
    useEffect(() => {
      if (!map) return;
      const info = L.DomUtil.create('div', 'legend');
  
      const positon = L.Control.extend({
        options: {
          position: 'bottomleft'
        },
  
        onAdd: function () {
          info.textContent = 'Click on map';
          return info;
        }
      })
  
      map.on('click', (e) => {
        info.textContent = e.latlng;
      })
  
      map.addControl(new positon());
  
    }, [map])
  
  
    return null
  
}

const GetCoordinates = (props) => {
    const map = useMap();
    const { action } = props;

    useEffect(() => {
        if (!map) return;

        const handleClick = (e) => {
            action(e.latlng);
        };

        map.on('click', handleClick);

        return () => {
            map.off('click', handleClick);
        };
    }, [map, action]);

    return null;
}
  
const GetZoom = (props) => {
    const map = useMap();
    const { action } = props;

    useEffect(() => {
        if (!map) return;

        const handleZoomEnd = () => {
            action(map.getZoom());
        };

        map.on('zoomend', handleZoomEnd);

        return () => {
            map.off('zoomend', handleZoomEnd);
        };
    
      }, [map, action])


    return null

}
  


const MapViewer = (props) => {
    const mapRef = useRef();
    const hasFitBoundsRef = useRef(false);

    const handleMapCreated = (map) => {
        mapRef.current = map;
        map.scrollWheelZoom.enable();
        map.doubleClickZoom.enable();
        map.touchZoom.enable();
        map.boxZoom.enable();
        map.keyboard.enable();
    };

    const [xmlData, setXmlData] = useState(null);
    const [nodes, setNodes] = useState(null);
    const [ways, setWays] = useState(null);

    const [LoadingFile, setLoadingFile] = useState(true);
    const [LoadingNode, setLoadingNode] = useState(true);
    const [LoadingWay, setLoadingWay] = useState(true);

    const center = useMemo(() => {
        let centerX = 0, centerY = 0;
        const nodeValues = nodes ? Object.values(nodes) : [];
        const len = nodeValues.length;
        if (len > 0) {
            nodeValues.forEach((value) => {
                centerX = centerX + value[0];
                centerY = centerY + value[1];
            });
            centerX = centerX / len;
            centerY = centerY / len;
        } else {
            const fallbackLat = parseFloat(props.center?.[0]);
            const fallbackLon = parseFloat(props.center?.[1]);
            centerX = Number.isFinite(fallbackLat) ? fallbackLat : 0;
            centerY = Number.isFinite(fallbackLon) ? fallbackLon : 0;
            console.warn('[MapViewer] no nodes, using fallback center', centerX, centerY);
        }
        return [centerX, centerY];
    }, [nodes, props.center]);
    


    // Effect 1: Fetch XML data when xmlFile prop changes
    useEffect(() => {
        const cacheBustedUrl = props.xmlFile ? `${props.xmlFile}?t=${Date.now()}` : props.xmlFile;
        console.log('[MapViewer] fetch XML', { xmlFile: props.xmlFile, cacheBustedUrl });
        hasFitBoundsRef.current = false;
        const fetchData = async () => {
            try {
                setLoadingFile(true);
                setXmlData(null);
                setNodes(null);
                setWays(null);
                setLoadingNode(true);
                setLoadingWay(true);

                const response = await fetch(cacheBustedUrl, { cache: 'no-store' });
                console.log('[MapViewer] fetch response', { ok: response.ok, status: response.status, statusText: response.statusText });
                const data = await response.text();
                console.log('[MapViewer] XML length', data.length);

                const parser = new DOMParser();
                const xmlDoc = parser.parseFromString(data, "text/xml");
                const parseErrors = xmlDoc.getElementsByTagName('parsererror');
                if (parseErrors && parseErrors.length > 0) {
                    console.error('[MapViewer] XML parse error', parseErrors[0].textContent);
                }
                setXmlData(xmlDoc);
                setLoadingFile(false);
            } catch (error) {
                console.error('[MapViewer] Error fetching XML file:', error);
                setLoadingFile(false);
            }
        };

        if (!props.xmlFile) {
            console.warn('[MapViewer] xmlFile is empty or undefined');
            return;
        }
        fetchData();
    }, [props.xmlFile]);

    // Effect 2: Parse nodes when xmlData changes
    useEffect(() => {
        if (!xmlData) return;

        console.log('[MapViewer] parsing nodes');
        const getNodes = function (xmlDoc, originLat, originLon) {
            const result = {};
            const nodesElements = xmlDoc.getElementsByTagName("node");
            for (let i = 0; i < nodesElements.length; i++) {
                const node = nodesElements[i];
                const id = node.getAttribute("id");
                let lat = parseFloat(node.getAttribute('lat'));
                let lon = parseFloat(node.getAttribute('lon'));

                // If lat/lon are empty/NaN, try to use local_x/local_y
                if (!Number.isFinite(lat) || !Number.isFinite(lon)) {
                    const tags = node.getElementsByTagName('tag');
                    let localX = null, localY = null;
                    for (let j = 0; j < tags.length; j++) {
                        const k = tags[j].getAttribute('k');
                        const v = tags[j].getAttribute('v');
                        if (k === 'local_x') localX = parseFloat(v);
                        if (k === 'local_y') localY = parseFloat(v);
                    }

                    // Convert local coords to lat/lon
                    if (Number.isFinite(localX) && Number.isFinite(localY)) {
                        const meters_per_degree = 111320;
                        lat = originLat + (localY / meters_per_degree);
                        lon = originLon + (localX / meters_per_degree);
                    }
                }

                if (Number.isFinite(lat) && Number.isFinite(lon)) {
                    result[id] = [lat, lon]
                }
            }
            return result;
        }

        const originLat = parseFloat(props.center?.[0]) || 0;
        const originLon = parseFloat(props.center?.[1]) || 0;
        const parsedNodes = getNodes(xmlData, originLat, originLon);
        console.log('[MapViewer] nodes parsed', Object.keys(parsedNodes).length, { originLat, originLon });
        setNodes(parsedNodes);
        setLoadingNode(false);
    }, [xmlData, props.center]);

    // Effect 3: Parse ways when nodes change
    useEffect(() => {
        if (!xmlData || !nodes) return;

        console.log('[MapViewer] parsing ways');
        const getWays = function (xmlDoc, nodesMap) {
            const result = [];
            const waysElements = xmlDoc.getElementsByTagName("way");
            for (let i = 0; i < waysElements.length; i++) {
                const way = waysElements[i];
                const nds = way.getElementsByTagName("nd");
                const nodeList = new Array(nds.length);
                for (let j = 0; j < nds.length; j++) {
                    nodeList[j] = nodesMap[nds[j].getAttribute("ref")];
                }
                const filtered = nodeList.filter((p) => Array.isArray(p) && Number.isFinite(p[0]) && Number.isFinite(p[1]));
                if (filtered.length > 1) {
                    result.push(filtered);
                }
            }
            return result;
        }

        const parsedWays = getWays(xmlData, nodes);
        console.log('[MapViewer] ways parsed', parsedWays.length);
        setWays(parsedWays);
        setLoadingWay(false);
    }, [xmlData, nodes]);

    useEffect(() => {
        if (mapRef.current && ways && ways.length > 0 && !hasFitBoundsRef.current) {
            const bounds = calculateBounds(ways);
            console.log('[MapViewer] fitBounds', bounds.length);
            mapRef.current.fitBounds(bounds);
            hasFitBoundsRef.current = true;
        }
    }, [ways]);

    // Function to calculate bounds of all polylines
    const calculateBounds = (polylines) => {
        let bounds = [];
        polylines.forEach((polyline) => {
            polyline.forEach((point) => {
                                if (point) {
                bounds = bounds.concat(L.latLng(point[0], point[1]));
                            }
            })
        });

        return bounds;
    };
    
    if(LoadingFile || LoadingNode || LoadingWay) {
        // console.log(LoadingFile, LoadingNode, LoadingWay)
        return (
            <MapContainer
                key={props.xmlFile || 'map'}
                style={{height:600, background: 'inherit'}}
                center={props.center}
                zoom={1}
                zoomControl={true}
                scrollWheelZoom={true}
                doubleClickZoom={true}
                touchZoom={true}
                boxZoom={true}
                keyboard={true}
                minZoom={1}
                maxZoom={22}
                whenCreated={handleMapCreated}
            />
        )
    }
    else {
        // console.log(center)
        

        return (
            <div className={props.classname}>
                <MapContainer
                    key={props.xmlFile || 'map'}
                    ref={mapRef}
                    style={{height:600, background: 'inherit'}} 
                    center={center} 
                    zoom={props.zoomLevel}
                    zoomControl={true}
                    scrollWheelZoom={true}
                    doubleClickZoom={true}
                    touchZoom={true}
                    boxZoom={true}
                    keyboard={true}
                    minZoom={1}
                    maxZoom={22}
                    whenCreated={handleMapCreated}
                    >
                        {/* <TileLayer
      attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
      url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
    /> */}
                        {
                            ways.map((points, idx) => {
                                    // console.log(points)
                                    return (
                                        <Polyline
                                            key={`lane-${idx}`}
                                            color={'red'}
                                            opacity={0.7}
                                            weight={2.5}
                                            positions={points}
                                        ></Polyline>
                                    );
                                }
                            )
                        }
                        <ShowCoordinates />
                        <GetZoom action={props.zoomAction} />
                        <GetCoordinates action={props.clickAction}/>
                        {
                            props.currentMarker.map( (p, idx) => {
                                    // console.log(p)
                                    return (
                                        <VehicleMarker key={`current-${p.scope}-${idx}`} pose={p} text={p.scope} type={"current"} zoom={props.zoomLevel}/>
                                    );
                                }

                            )
                        }
                        {/* <VehicleMarker pose={props.currentMarker} text={"Ego Position"}/> */}
                        {/* <VehicleMarker pose={props.initMarker} text={"Initialized Position"}/> */}
                        {
                            props.goalMarker.map( (p, idx) => {
                                    return (
                                        <VehicleMarker key={`goal-${p.scope}-${idx}`} pose={p} text={`Goal of ${p.scope}`} type={"goal"} zoom={props.zoomLevel}/>
                                    );
                                }

                            )
                        }
                        <VehicleMarker pose={props.setGoalMarker} text={"Goal Position"} type={"setGoal"} zoom={props.zoomLevel}/>
                </MapContainer>
            </div>
        )
    }
    
}

export default MapViewer;