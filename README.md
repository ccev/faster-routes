## This repo is no longer maintained

Due to a lack of motivation and time, I've decided to archive most of my repos. At the time of writing this, it's still fully functional.

faster-routes is a pretty cool tool to generate a quick base route for you, that should then be edited manually in order to fully maximize scans. The only improvement I thought of would be to make the workflow a bit easier. By integrating Tabbo's overwrite route script into it and grabbing the spawns and geofence from the madmin API. Also it should be able to handle multipolygons. Shouldn't be too hard

# faster-routes
An alternate routecalc algorithm for MAD (made quick and dirty)

### How to use

This is a recommendation of how to use this script. It requires a bit of setup but the workflow in the end is pretty good. Note that I set up everything (except the MAD instance) on my own computer since it takes quite a bit of computing.

- `git clone https://github.com/ccev/faster-routes.git && cd faster-routes && cp config-example.json config.json`, then fill in the config's db part
- Clone `git clone https://github.com/Tabbomat/MADUtilities.git` and fill in its config
- In the faster-routes directory, create a new file `fence.txt`. This file should contain the geofence you want your route to be calculated it in. Copy the text from MADmin - Settings - Geofences - Edit
- Run `cluster.py`
- A file called `route.txt` will be created. Copy that to your MADUtilities directory. Then run `overwrite_route.py` there
- Finished. For further improvement I highly recommend viewing the route in MADmin and edit it

If you want to create a new route, just change `faster-routes/fence.txt`, run `cluster.py`, copy `route.txt` to MADutilities, run `overwrite_route.py`, go to MADmin and review the results.

### How it works and what te config does

- Go through each pair of spawns that are within `max_distance_between_spawns` meters of one another, find the middle point and save it together with the spawns in its `view_distance` meter range if it covers more than `min_total_spawns_in_cluster` spawns. These will be all possible clusters we'll now check
- Go through each spawnpoint, find all clusters containing this spawnpoint and save the one containing the most overall spawnpoints. This is how the main route will be built
- Go through all routepoints and remove clusters that have added less than `min_added_spawns_in_cluster`. So if a cluster covers a total of 5 spawns, but those 5 spawns are already covered by other clusters, that cluster will be removed. If you raise this number, you can later manually add the missed spawns yourself.
- The script will then try to "group" clusters

### Possible improvements
- Improve the way of generating possible routepoints (step 1) - currently a lot of power will be wasted on creating points in positions where there already is one close enough where it doesn't make a difference. Maybe add an option to save points from every ~5m² in the area. Would take ages to process but should greatly improve results
- In the last step, try to recursively go through the route, delete a random routepoint and then try to cover it up with nearby points. Then do the same for those nearby points. Something like that. 
