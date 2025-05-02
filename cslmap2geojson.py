import xml.etree.ElementTree as ET
import json
import configparser

def xml_to_geojson_layers(xml_string, enable_3d = False):
    """
    Converts an XML string containing game coordinates and segment types
    to separate GeoJSON FeatureCollections for different feature types (layers).

    Parses elements like Nodes, Segments, Buildings, Districts, Parks, Transports,
    and SegmentTypes. Uses X and Z as horizontal coordinates and includes Y as elevation property.
    Includes segment type details as properties for Segment features.

    Args:
        xml_string: A string containing the XML data.
        enable_3d: Flag to try to read 3D height data.

    Returns:
        A dictionary where keys are layer names (e.g., 'Buildings', 'Segments') and
        values are lists of GeoJSON features for that layer. Returns an empty dictionary
        if parsing fails or no features are found.
    """
    layers = {
        "Nodes": [],
        "Segments": [],
        "Buildings": [],
        "Districts": [],
        "Parks": [],
        "Transports": []
        # Add other potential layers if needed based on your XML
    }
    # Dictionary to store node ID and [x, z, y] coordinates for Transport features lookup
    node_coordinates_xyz = {}
    # Dictionary to store segment type details, keyed by name
    segment_types_data = {}

    try:
        # Parse the XML data from the string
        root = ET.fromstring(xml_string)

        # --- Process SegmentTypes ---
        segment_types_element = root.find('SegmentTypes')
        if segment_types_element is not None:
            for st in segment_types_element.findall('ST'):
                st_name = st.get('name')
                if st_name:
                    segment_type_details = {
                        "highway": st.get('highway'),
                        "lanes": []
                    }
                    lanes_element = st.find('Lanes')
                    if lanes_element is not None:
                        for lane in lanes_element.findall('Lane'):
                            lane_details = {
                                "type": lane.get('type'),
                                "vType": lane.get('vType'),
                                "dir": lane.get('dir'),
                                "pos": lane.get('pos'),
                                "width": lane.get('width'),
                                "speed": lane.get('speed')
                            }
                            segment_type_details["lanes"].append(lane_details)
                    segment_types_data[st_name] = segment_type_details
        # print(f"Parsed {len(segment_types_data)} segment types.") # Debugging line


        # --- Process Nodes ---
        nodes_element = root.find('Nodes')
        if nodes_element is not None:
            for node in nodes_element.findall('Node'):
                node_id = node.get('id')
                pos = node.find('Pos')
                if pos is not None:
                    x = pos.get('x')
                    y = pos.get('y')
                    z = pos.get('z')
                    if x is not None and z is not None: # Require X and Z for horizontal position
                        try:
                            coord_x = float(x)
                            coord_z = float(z)

                            # Store node coordinates [x, z, y] for later use by Transports
                            if node_id:
                                coord_y = float(y) if y is not None and enable_3d else None
                                node_coordinates_xyz[node_id] = [coord_x, coord_z, coord_y]

                            # GeoJSON coordinates for 2D visualization: [x, z]
                            geojson_coords = [coord_x, coord_z]
                            # If you want 3D GeoJSON, uncomment the line below and add coord_y
                            if y is not None and enable_3d:
                                try:
                                    coord_y = float(y)
                                    geojson_coords.append(coord_y)
                                except ValueError:
                                     print(f"Warning: Could not convert Y coordinate for Node id={node_id}: y={y}. Storing as property.")
                                     coord_y = None # Ensure coord_y is None if conversion fails


                            # Create a GeoJSON Point feature for the Node
                            point_feature = {
                                "type": "Feature",
                                "geometry": {
                                    "type": "Point",
                                    "coordinates": geojson_coords # Using [x, z] for 2D representation
                                },
                                "properties": {
                                    "id": node_id,
                                    "elev": node.get('elev'), # Keep original elev property
                                    "ug": node.get('ug'),
                                    "og": node.get('og'),
                                    "srv": node.get('srv'),
                                    "subsrv": node.get('subsrv'),
                                    "dist": node.get('dist')
                                }
                            }
                            # Add elevation as a property if y was available
                            if y is not None and enable_3d:
                                try:
                                    point_feature["properties"]["elevation"] = float(y)
                                except ValueError:
                                     # Already warned above, just don't add property if invalid
                                     pass

                            layers["Nodes"].append(point_feature)
                        except ValueError:
                            print(f"Warning: Could not convert X or Z coordinates for Node id={node_id}: x={x}, z={z}. Skipping node.")
                            continue

        # --- Process Segments ---
        segments_element = root.find('Segments')
        if segments_element is not None:
            for seg in segments_element.findall('Seg'):
                seg_id = seg.get('id')
                icls = seg.get('icls') # Get the segment type name
                points_element = seg.find('Points')
                if points_element is not None:
                    line_coordinates = []
                    segment_elevations = [] # Store y values for segments
                    for p in points_element.findall('P'):
                        x = p.get('x')
                        y = p.get('y')
                        z = p.get('z')
                        if x is not None and z is not None: # Require X and Z for horizontal position
                            try:
                                coord_x = float(x)
                                coord_z = float(z)
                                # GeoJSON coordinates for 2D visualization: [x, z]
                                point_geojson_coords = [coord_x, coord_z]
                                # If you want 3D GeoJSON, uncomment the line below and add coord_y
                                if y is not None and enable_3d:
                                    try:
                                        coord_y = float(y)
                                        point_geojson_coords.append(coord_y)
                                    except ValueError:
                                        print(f"Warning: Could not convert Y coordinate for Point in Segment id={seg_id}: y={y}. Skipping Y for this point.")

                                line_coordinates.append(point_geojson_coords)

                                # Store elevation
                                if y is not None and enable_3d:
                                     try:
                                         segment_elevations.append(float(y))
                                     except ValueError:
                                         pass # Ignore if y is not a valid number

                            except ValueError:
                                print(f"Warning: Could not convert X or Z coordinates for Point in Segment id={seg_id}: x={x}, z={z}. Skipping point.")
                                continue

                    if line_coordinates:
                        # Create a GeoJSON LineString feature for the Segment
                        line_feature = {
                            "type": "Feature",
                            "geometry": {
                                "type": "LineString",
                                "coordinates": line_coordinates # Using [x, z] for 2D representation
                            },
                            "properties": {
                                "id": seg_id,
                                "sn": seg.get('sn'),
                                "en": seg.get('en'),
                                "icls": icls, # Include the segment type name
                                "width": seg.get('width'),
                                "name": seg.findtext('Name')
                                # Note: Path data is not included as geometry, could add to properties if needed
                            }
                        }
                        # Add elevations as a property (e.g., a list of elevations per point)
                        if segment_elevations:
                             line_feature["properties"]["elevations"] = segment_elevations

                        # Add segment type details from SegmentTypes if available
                        if icls and icls in segment_types_data:
                            line_feature["properties"]["segment_type_details"] = segment_types_data[icls]
                        elif icls:
                             print(f"Warning: Segment type '{icls}' not found in SegmentTypes for Segment id={seg_id}.")


                        layers["Segments"].append(line_feature)

        # --- Process Terrains ---
        # The format of Terrains data (e.g., "142:1990,81:2051,...") is not a standard
        # geometric type (Point, LineString, Polygon) that can be directly represented
        # in GeoJSON without further interpretation of what these pairs represent spatially.
        # Skipping Terrains for standard GeoJSON geometry features.
        terrains_element = root.find('Terrains')
        if terrains_element is not None:
             print("Note: Terrains data format is not standard GeoJSON geometry and is skipped.")
             # If you need to include this data, you could add it as a property
             # to a single feature representing the entire terrain area, or
             # process it differently if you know its spatial representation.


        # --- Process Buildings ---
        buildings_element = root.find('Buildings')
        if buildings_element is not None:
            for buil in buildings_element.findall('Buil'):
                buil_id = buil.get('id')
                points_element = buil.find('Points')
                if points_element is not None:
                    polygon_coordinates = []
                    building_elevations = [] # Store y values for buildings
                    for p in points_element.findall('P'):
                        x = p.get('x')
                        y = p.get('y')
                        z = p.get('z')
                        if x is not None and z is not None: # Require X and Z for horizontal position
                            try:
                                coord_x = float(x)
                                coord_z = float(z)
                                # GeoJSON coordinates for 2D visualization: [x, z]
                                point_geojson_coords = [coord_x, coord_z]
                                # If you want 3D GeoJSON, uncomment the line below and add coord_y
                                if y is not None and enable_3d:
                                    try:
                                        coord_y = float(y)
                                        point_geojson_coords.append(coord_y)
                                    except ValueError:
                                         print(f"Warning: Could not convert Y coordinate for Point in Building id={buil_id}: y={y}. Skipping Y for this point.")

                                polygon_coordinates.append(point_geojson_coords)

                                # Store elevation
                                if y is not None and enable_3d:
                                     try:
                                         building_elevations.append(float(y))
                                     except ValueError:
                                         pass # Ignore if y is not a valid number

                            except ValueError:
                                print(f"Warning: Could not convert X or Z coordinates for Point in Building id={buil_id}: x={x}, z={z}. Skipping point.")
                                continue

                    if polygon_coordinates:
                        # GeoJSON Polygons require the first and last coordinate to be the same.
                        # Add the first point to the end if the polygon is not closed.
                        if polygon_coordinates[0] != polygon_coordinates[-1]:
                             polygon_coordinates.append(polygon_coordinates[0])
                             # Also duplicate the elevation if storing per-point elevations
                             if building_elevations:
                                 building_elevations.append(building_elevations[0])


                        # Create a GeoJSON Polygon feature for the Building
                        polygon_feature = {
                            "type": "Feature",
                            "geometry": {
                                "type": "Polygon",
                                "coordinates": [polygon_coordinates] # Polygon coordinates are an array of rings
                            },
                            "properties": {
                                "id": buil_id,
                                "name": buil.get('name'),
                                "srv": buil.get('srv'),
                                "subsrv": buil.get('subsrv'),
                                "icls": buil.get('icls')
                            }
                        }
                         # Add elevations as a property (e.g., a list of elevations per point)
                        if building_elevations:
                             polygon_feature["properties"]["elevations"] = building_elevations

                        layers["Buildings"].append(polygon_feature)

        # --- Process Districts ---
        districts_element = root.find('Districts')
        if districts_element is not None:
            for dist in districts_element.findall('Dist'):
                dist_id = dist.get('id')
                p = dist.find('P')
                if p is not None:
                    x = p.get('x')
                    y = p.get('y')
                    z = p.get('z')
                    if x is not None and z is not None: # Require X and Z for horizontal position
                        try:
                            coord_x = float(x)
                            coord_z = float(z)
                             # GeoJSON coordinates for 2D visualization: [x, z]
                            geojson_coords = [coord_x, coord_z]
                            # If you want 3D GeoJSON, uncomment the line below and add coord_y
                            if y is not None and enable_3d:
                                try:
                                    coord_y = float(y)
                                    geojson_coords.append(coord_y)
                                except ValueError:
                                     print(f"Warning: Could not convert Y coordinate for District id={dist_id}: y={y}. Storing as property.")
                                     coord_y = None # Ensure coord_y is None if conversion fails


                            # Create a GeoJSON Point feature for the District centroid
                            point_feature = {
                                "type": "Feature",
                                "geometry": {
                                    "type": "Point",
                                    "coordinates": geojson_coords # Using [x, z] for 2D representation
                                },
                                "properties": {
                                    "id": dist_id,
                                    "name": dist.get('name')
                                }
                            }
                            # Add elevation as a property if y was available
                            if y is not None and enable_3d:
                                try:
                                    point_feature["properties"]["elevation"] = float(y)
                                except ValueError:
                                     # Already warned above, just don't add property if invalid
                                     pass

                            layers["Districts"].append(point_feature)
                        except ValueError:
                            print(f"Warning: Could not convert X or Z coordinates for District id={dist_id}: x={x}, z={z}. Skipping district.")
                            continue

        # --- Process Parks ---
        parks_element = root.find('Parks')
        if parks_element is not None:
            for park in parks_element.findall('Park'):
                park_id = park.get('id')
                p = park.find('P')
                if p is not None:
                    x = p.get('x')
                    y = p.get('y')
                    z = p.get('z')
                    if x is not None and z is not None: # Require X and Z for horizontal position
                        try:
                            coord_x = float(x)
                            coord_z = float(z)
                            # GeoJSON coordinates for 2D visualization: [x, z]
                            geojson_coords = [coord_x, coord_z]
                            # If you want 3D GeoJSON, uncomment the line below and add coord_y
                            if y is not None and enable_3d:
                                try:
                                    coord_y = float(y)
                                    geojson_coords.append(coord_y)
                                except ValueError:
                                     print(f"Warning: Could not convert Y coordinate for Park id={park_id}: y={y}. Storing as property.")
                                     coord_y = None # Ensure coord_y is None if conversion fails


                            # Create a GeoJSON Point feature for the Park location
                            point_feature = {
                                "type": "Feature",
                                "geometry": {
                                    "type": "Point",
                                    "coordinates": geojson_coords # Using [x, z] for 2D representation
                                },
                                "properties": {
                                    "id": park_id,
                                    "name": park.get('name'),
                                    "type": park.findtext('type')
                                }
                            }
                             # Add elevation as a property if y was available
                            if y is not None and enable_3d:
                                try:
                                    point_feature["properties"]["elevation"] = float(y)
                                except ValueError:
                                     # Already warned above, just don't add property if invalid
                                     pass

                            layers["Parks"].append(point_feature)
                        except ValueError:
                            print(f"Warning: Could not convert X or Z coordinates for Park id={park_id}: x={x}, z={z}. Skipping park.")
                            continue

        # --- Process Transports ---
        transports_element = root.find('Transports')
        if transports_element is not None:
            for trans in transports_element.findall('Trans'):
                trans_id = trans.get('id')
                trans_name = trans.get('name')
                trans_type = trans.get('type')
                stops_element = trans.find('Stops')
                if stops_element is not None:
                    route_coordinates = []
                    route_elevations = [] # Store y values for transport stops
                    for stop in stops_element.findall('Stop'):
                        node_ref = stop.get('node')
                        if node_ref in node_coordinates_xyz:
                            # Get the [x, z, y] coordinates from the stored node data
                            coords_xyz = node_coordinates_xyz[node_ref]
                            # Use [x, z] for the GeoJSON LineString
                            route_coordinates.append([coords_xyz[0], coords_xyz[1]])
                            # Store the elevation (y)
                            if coords_xyz[2] is not None:
                                route_elevations.append(coords_xyz[2])

                        else:
                            print(f"Warning: Node reference {node_ref} not found in Nodes section for Transport id={trans_id}. Skipping stop.")

                    if route_coordinates:
                         # Create a GeoJSON LineString feature for the Transport route
                        line_feature = {
                            "type": "Feature",
                            "geometry": {
                                "type": "LineString",
                                "coordinates": route_coordinates # Using [x, z] for 2D representation
                            },
                            "properties": {
                                "id": trans_id,
                                "name": trans_name,
                                "type": trans_type,
                                # You could also include color if needed, parsing the 'color' element
                            }
                        }
                        # Add elevations as a property (e.g., a list of elevations per point)
                        if route_elevations:
                             line_feature["properties"]["elevations"] = route_elevations

                        layers["Transports"].append(line_feature)


    except ET.ParseError as e:
        print(f"Error parsing XML: {e}")
        return {} # Return empty dictionary on parsing error
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return {} # Return empty dictionary on other errors

    return layers

# --- How to use the script ---

# --- IMPORTANT: Adjust the parsing logic above (e.g., root.findall and attribute names)
# --- to match the actual structure of your game's XML file.
# --- The current example assumes coordinates are attributes of direct children of the root
# --- or within a nested tag like <Position>. You will need to inspect your XML.

# Example of how to read from a file instead of a string:
xml_file = 'example.xml'
config = configparser.RawConfigParser()
config.read('config.ini')
xml_file = config.get("csl_settings", "xml_file")
enable_3d_str = config.get("csl_settings", "enable_3d")
if enable_3d_str.upper() == "TRUE":
    enable_3d = True
else:
    enable_3d = False

try:
    with open(xml_file, 'r') as f:
        xml_data_string = f.read()
except FileNotFoundError:
    print("Error: xml file not found. Please provide the correct path.")
    xml_data_string = None # Set to None to avoid processing

if xml_data_string:
    geojson_layers = xml_to_geojson_layers(xml_data_string, enable_3d)

    if geojson_layers:
        print("Generated GeoJSON layers:")
        for layer_name, features in geojson_layers.items():
            if features: # Only create a file if the layer has features
                geojson_data = {
                    "type": "FeatureCollection",
                    "features": features
                }
                file_name = f"{layer_name.lower()}.geojson"
                with open(file_name, 'w') as f:
                    json.dump(geojson_data, f, indent=2)
                print(f"- Saved {len(features)} features to {file_name}")
            else:
                 print(f"- No features found for layer: {layer_name}")
