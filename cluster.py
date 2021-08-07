from pymysql import connect
from math import sin, cos, sqrt, atan2, radians
import math
import random
from geopy import distance as calc_distance
import pickle

def get_distance(point1, point2):
    # approximate radius of earth in km
    earth_radius = 6373.0

    lat1 = math.radians(point1[0])
    lon1 = math.radians(point1[1])
    lat2 = math.radians(point2[0])
    lon2 = math.radians(point2[1])

    dlon = lon2 - lon1
    dlat = lat2 - lat1

    angle = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    circ = 2 * math.atan2(math.sqrt(angle), math.sqrt(1 - angle))

    distance = earth_radius * circ

    return distance * 1000

def get_middle_of_coord_list(list_of_coords):
    if len(list_of_coords) == 1:
        return list_of_coords[0]

    coord_x = 0
    coord_y = 0
    coord_z = 0

    for coord in list_of_coords:
        # transform to radians...
        lat_rad = math.radians(coord.lat)
        lng_rad = math.radians(coord.lon)

        coord_x += math.cos(lat_rad) * math.cos(lng_rad)
        coord_y += math.cos(lat_rad) * math.sin(lng_rad)
        coord_z += math.sin(lat_rad)

    amount_of_coords = len(list_of_coords)
    coord_x = coord_x / amount_of_coords
    coord_y = coord_y / amount_of_coords
    coord_z = coord_z / amount_of_coords
    central_lng = math.atan2(coord_y, coord_x)
    central_square_root = math.sqrt(coord_x * coord_x + coord_y * coord_y)
    central_lat = math.atan2(coord_z, central_square_root)

    return (math.degrees(central_lat), math.degrees(central_lng))

import json
with open("config.json", "r") as f:
    config = json.load(f)
max_distance = config["view_distance"]

class Spawn:
    def __init__(self, sid, lat, lon):
        self.lat = lat
        self.lon = lon
        self.id = sid
        self.done = False
        self.clusters = []

class Range:
    def __init__(self, lat, lon):
        self.lat = lat
        self.lon = lon

        self.spawns = []
        self.double_spawns = []

    def get_spawns(self):
        return [spawn for spawn in self.spawns if not spawn.done]

    def get_done_spawns(self):
        return [spawn for spawn in self.spawns if spawn.done]

    def get_spawn_id(self):
        return [s.id for s in self.get_spawns()]

    @property
    def unique_spawns(self):
        return [s for s in self.spawns if s.id not in [d.id for d in self.double_spawns]]

def get_spawns():
    connection = connect(
        host=config["host"],
        user=config["user"],
        password=config["password"],
        database=config["db_name"],
        port=config["port"],
        autocommit=True
    )

    with open("fence.txt", "r") as f:
        area = f.read()

    area = area.replace(",", " ").strip("\n")
    area = area.split("\n")
    area.append(area[0])
    area = ",".join(area)
    cursor = connection.cursor()
    query = f"select spawnpoint, latitude, longitude from trs_spawn where ST_CONTAINS(ST_GEOMFROMTEXT('POLYGON(({area}))'), point(latitude, longitude)) and eventid = 1 order by longitude, latitude"
    cursor.execute(query)

    r = cursor.fetchall()
    cursor.close()
    connection.close()

    spawns = []
    for sid, (ssid, lat, lon) in enumerate(r):
        spawns.append(Spawn(ssid, lat, lon))

    return spawns

spawns = get_spawns()

def middle_points():
    points = []
    i = 1
    total = f"{len(spawns)}"
    for spawn1 in spawns:
        for spawn2 in spawns:
            distance = get_distance((spawn1.lat, spawn1.lon), (spawn2.lat, spawn2.lon))
            if distance < config["max_distance_between_spawns"]:
                middle = get_middle_of_coord_list([spawn1, spawn2])
                routepoint = Range(middle[0], middle[1])
                for spawn3 in spawns:
                    if get_distance(middle, (spawn3.lat, spawn3.lon)) <= max_distance:
                        routepoint.spawns.append(spawn3)
                spawn_amount = len(routepoint.spawns)
                if spawn_amount >= config["min_total_spawns_in_cluster"]:
                    points.append(routepoint)
        i += 1
        print(f"Generating possible routepoints: {i}/{total}")
    return points

def point_points():
    points = []
    i = 1
    total = len(spawns)
    for spawn in spawns:
        routepoint = Range(spawn.lat, spawn.lon)
        for spawn3 in spawns:
            if get_distance((spawn.lat, spawn.lon), (spawn3.lat, spawn3.lon)) <= max_distance:
                routepoint.spawns.append(spawn3)
        spawn_amount = len(routepoint.spawns)
        if spawn_amount > 0:
            print(f"{i}/{total}: {spawn_amount}")
            points.append(routepoint)
        i += 1
    return points

"""try:
    with open("points.pickle", "rb") as handle:
        spawns, points = pickle.load(handle)
except:
    points = middle_points()
    to_save = (spawns, points)

    with open("points.pickle", "wb") as handle:
        pickle.dump(to_save, handle)"""

points = middle_points()


def cluster_v1(spawns, final=[]):
    total = len(spawns)
    final_len = 0
    for i, spawn in enumerate(spawns, start=1):
        if spawn.done:
            continue
        circles = []
        for point in points:
            if spawn.id in point.get_spawn_id():
                circles.append(point)
        if len(circles) == 0:
            continue
        circle = max(circles, key=lambda point: (len(point.get_spawns())))
        for circlespawn in circle.get_spawns():
            circlespawn.done = True
        final_len += 1

        final.append(circle)
        print(f"Generating route: {i}/{total} (length: {final_len})")
    return final

"""try:
    with open("route.pickle", "rb") as handle:
        final = pickle.load(handle)
except:
    final = cluster_v1(spawns)

    with open("route.pickle", "wb") as handle:
        pickle.dump(final, handle)"""
final = cluster_v1(spawns)

def check_doubles(cluster_list):
    for cluster in cluster_list:
        cluster_ids = [s.id for s in cluster.spawns]
        for cluster2 in cluster_list:
            if cluster2 == cluster:
                continue
            for spawn in cluster2.spawns:
                if spawn.id in cluster_ids:
                    if spawn.id not in [s.id for s in cluster2.double_spawns]:
                        cluster2.double_spawns.append(spawn)
    return cluster_list

def check_final_route(final):
    total_removed = 0
    
    for cluster in final:
        if len(cluster.spawns) - len(cluster.double_spawns) < config["min_added_spawns_in_cluster"]:
            recheck_clusters = []
            for spawn in cluster.spawns:
                recheck_clusters += spawn.clusters

            final.remove(cluster)
            total_removed += 1
            check_doubles(recheck_clusters)
            print("Removed one point from route that didn't add enough spawns")
    if total_removed > 0:
        final = check_final_route(final)
    return final

def edit_route(smallest, route):
    for spawn in smallest.spawns:
        for point in points:
            if not spawn.id in [s.id for s in point.spawns]:
                continue
            if point == smallest:
                continue

            other_clusters = []
            for spawn2 in point.spawns:
                for cluster in spawn2.clusters:
                    if cluster != smallest and cluster not in other_clusters and cluster in route:
                        other_clusters.append(cluster)

            if len(other_clusters) == 0:
                continue

            for cluster in other_clusters:
                all_spawns = smallest.unique_spawns + cluster.unique_spawns

                if [1 for s in all_spawns if s.id not in [s.id for s in point.spawns]]:
                    continue

                print("Optimize: Merged 2 routepoints")
                route.remove(cluster)
                route.remove(smallest)
                route.append(point)
                return

for circle in final:
    for spawn in circle.spawns:
        spawn.clusters.append(circle)

check_doubles(final)
final = check_final_route(final)

final_len = len(final)
for i in range(final_len):
    try:
        smallest = final[i]
    except:
        break
    edit_route(smallest, final)

final = check_final_route(final)


route = ""
for circle in final:
    route += f"{circle.lat},{circle.lon}\n"

print(f"Wrote route to route.txt. Total length: {len(final)}")

with open("route.txt", "w+") as f:
    f.write(route)
