import xml.dom.minidom
import dateutil.parser
import datetime

class TrackPoint:
    def __init__(self, trackPointNode = None):
        self.distance = 0.0
        self.time = None
        self.velocity = 0.0
        if (trackPointNode == None):
            return
        distanceMetersNodeList = trackPointNode.getElementsByTagName(
            "DistanceMeters")
        if (len(distanceMetersNodeList) != 1):
            return None
        distanceMetersNode = distanceMetersNodeList[0]
        distanceText = distanceMetersNode.childNodes[0].nodeValue
        self.distance = float(distanceText)
        # Time
        timeNodeList = trackPointNode.getElementsByTagName("Time")
        if (len(timeNodeList) != 1):
            return None
        timeNode = timeNodeList[0]
        timeText = timeNode.childNodes[0].nodeValue
        self.time = dateutil.parser.parse(timeText)

    def __str__(self):
        return "Distance: {} (Velocity: {} Time: {})\n".format(self.distance, self.velocity, str(self.time))

    def distanceTo(self, other):
        return other.distance - self.distance

    def timeTo(self, other):
        return (other.time - self.time).total_seconds()


class Track:
    def __init__(self, trackNode = None):
        self.trackpoints = []
        if (trackNode == None):
            return
        for trackChild in trackNode.childNodes:
            if (trackChild.nodeName != "Trackpoint"):
                continue
            tp = TrackPoint(trackChild)
            if (tp.time != None):
                self.trackpoints.append(tp)

    def __str__(self):
        serialized = "Track with {} points.\n".format(len(self.trackpoints))
        for tp in self.trackpoints[:5]:
            serialized = serialized + str(tp)
        serialized = serialized + "...\n"
        for tp in self.trackpoints[-5:]:
            serialized = serialized + str(tp)
        return serialized


class Lap:
    def __init__(self, lapNode = None):
        self.tracks = []
        if (lapNode == None):
            return
        for lapChild in lapNode.childNodes:
            if (lapChild.nodeName == "Track"):
                track = Track(lapChild)
                self.tracks.append(track)

    def __str__(self):
        serialized = "Lap with {} tracks.\n".format(len(self.tracks))
        for t in self.tracks:
            serialized = serialized + str(t)
        return serialized

    def allTrackPoints(self):
        allTp = []
        for t in self.tracks:
            allTp.extend(t.trackpoints)
        return allTp


class Activity:
    span_distances = [400, 1000, 2000, 3000,
                      5000, 10000, 20000, 21097.5, 42193]

    def __init__(self, activityNode = None):
        self.sport = "Running"
        self.laps = []
        self.bestSpans = []
        if (activityNode == None):
            return
        self.sport = activityNode.attributes["Sport"].nodeValue
        for activityChild in activityNode.childNodes:
            if (activityChild.nodeName != "Lap"):
                continue
            lap = Lap(activityChild)
            self.laps.append(lap)
        self.addVelocities()
        self.addBestSpans()

    def __str__(self):
        serialized = "Activity of type {} with {} laps.\n".format(
            self.sport, len(self.laps))
        for l in self.laps:
            serialized = serialized + str(l)
        for t, dist in zip(self.bestSpans, Activity.span_distances[0:len(self.bestSpans)]):
            serialized = serialized + \
                "{}: {}\n".format(dist, str(datetime.timedelta(seconds=t)))
        return serialized

    def allTrackPoints(self):
        allTp = []
        for l in self.laps:
            allTp.extend(l.allTrackPoints())
        return allTp

    def addVelocities(self):
        allTp = self.allTrackPoints()
        allVelocities = [0.0]
        for b, a in zip(allTp[:-2], allTp[2:]):
            distance = a.distance - b.distance
            time = a.time - b.time
            velocity = distance/time.total_seconds()
            # convert m/s to km/h
            velocity *= 3.6
            allVelocities.append(velocity)
        allVelocities.append(0.0)
        # smooth over 3 values
        for tp, v1, v2, v3 in zip(allTp[1:-1], allVelocities[:-2], allVelocities[1:-1], allVelocities[2:]):
            tp.velocity = (v1 + v2 + v3)/3.0

    def bestSpan(self, distance=400):
        '''
        Return the time for the best span of the given distance
        '''
        allTp = self.allTrackPoints()
        span = [0, 1]
        best_time = -1
        if allTp[0].distanceTo(allTp[-1]) < distance:
            return best_time
        while True:
            # increase the second index until the distance is larger than
            # distance
            while allTp[span[0]].distanceTo(allTp[span[1]]) < distance:
                if span[1] < len(allTp)-2:
                    span[1] = span[1] + 1
                else:
                    return best_time

            actual_distance = allTp[span[0]].distanceTo(allTp[span[1]])
            time = allTp[span[0]].timeTo(
                allTp[span[1]]) * (distance/actual_distance)
            best_time = time if (
                time < best_time or best_time == -1) else best_time

            span[0] = span[0] + 1

    def addBestSpans(self):
        self.bestSpans = []
        for distance in Activity.span_distances:
            time = self.bestSpan(distance)
            if time != -1:
                self.bestSpans.append(time)


class TrainingCenterDatabase:
    def __init__(self, filename):
        self.activities = []
        dom = xml.dom.minidom.parse(filename)
        tcdNode = dom.getElementsByTagName("TrainingCenterDatabase")[0]
        for activities in tcdNode.childNodes:
            for activityNode in activities.childNodes:
                if activityNode.nodeName != "Activity":
                    continue
                activity = Activity(activityNode)
                self.activities.append(activity)

    def __str__(self):
        serialized = "TrainingCenterDatabase with {} activities\n".format(
            len(self.activities))
        for act in self.activities:
            serialized = serialized + str(act)
        return serialized

tcd = TrainingCenterDatabase(
    './tcxdata/2019-05-28T11_45_53.000Z_3528649242.tcx')
print(tcd)
