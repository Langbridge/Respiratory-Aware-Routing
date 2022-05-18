import gpxpy
import gpxpy.gpx
import xml.etree.cElementTree as ET
import datetime as dt

gpx_file = open('A/0605PM.gpx', 'r')
gpx = gpxpy.parse(gpx_file)

# true_time = dt.datetime(2022, 5, 9, 7, 56)
true_time = dt.datetime(2022, 5, 6, 17, 7)
print(true_time)
start_time = None
for track in gpx.tracks:
    for segment in track.segments:
        for point in segment.points:
            if start_time == None:
                start_time = point.time.replace(tzinfo=None)
                t_offset = start_time-true_time
                print(f"Time offset is {t_offset}")

            point.time = point.time - t_offset
            print('Point at ({0},{1}) -> {2}'.format(point.latitude, point.longitude, point.time))

with open("test.gpx", "w") as f:
    f.write(gpx.to_xml())