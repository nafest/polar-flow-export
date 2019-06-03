import xml.dom.minidom
import dateutil.parser
import datetime
import time
import tcx_pb2
import glob
import os

def getChildByTagName(node, name):
    return list(filter(lambda n: n.nodeName == name, node.childNodes))

def getStringValue(parentNode, name):
    tagNodeList = getChildByTagName(parentNode, name)
    if (len(tagNodeList) == 1):
        node = tagNodeList[0]
        return node.childNodes[0].nodeValue
    else:
        return ""


def getFloatValue(parentNode, name):
    tagNodeList = getChildByTagName(parentNode, name)
    if (len(tagNodeList) == 1):
        node = tagNodeList[0]
        return float(node.childNodes[0].nodeValue)
    else:
        return 0.0


def getIntValue(parentNode, name):
    tagNodeList = getChildByTagName(parentNode, name)
    if (len(tagNodeList) == 1):
        node = tagNodeList[0]
        return int(node.childNodes[0].nodeValue)
    else:
        return 0


def getBoolValue(parentNode, name, trueString="True"):
    tagNodeList = getChildByTagName(parentNode, name)
    if (len(tagNodeList) == 1):
        node = tagNodeList[0]
        return node.childNodes[0].nodeValue == trueString
    else:
        return False


def getTimeValue(parentNode, name, trueString="True"):
    tagNodeList = getChildByTagName(parentNode, name)
    if (len(tagNodeList) == 1):
        node = tagNodeList[0]
        return dateutil.parser.parse(node.childNodes[0].nodeValue)
    else:
        return None


def getNestedIntValue(parentNode, nested, name):
    tagNodeList = getChildByTagName(parentNode, nested)
    if (len(tagNodeList) == 1):
        node = tagNodeList[0]
        return getIntValue(node, name)
    else:
        return 0


def getNestedFloatValue(parentNode, nested, name):
    tagNodeList = getChildByTagName(parentNode, nested)
    if (len(tagNodeList) == 1):
        node = tagNodeList[0]
        return getFloatValue(node, name)
    else:
        return 0.0


class TrackPoint:
    def __init__(self, trackPointNode=None):
        self.distance = 0.0
        self.time = None
        self.velocity = 0.0
        self.latitude = 0.0
        self.longitude = 0.0
        self.altitude = 0.0
        self.heartrate = 0.0
        self.cadence = 0.0
        self.sensorPresent = False
        if (trackPointNode == None):
            return
        # Distance
        self.distance = getFloatValue(trackPointNode, "DistanceMeters")
        # Time
        self.time = getTimeValue(trackPointNode, "Time")
        # Position
        self.latitude = getNestedFloatValue(
            trackPointNode, "Position", "LatitudeDegrees")
        self.longitude = getNestedFloatValue(
            trackPointNode, "Position", "LongitudeDegrees")
        # altitude
        self.altitude = getFloatValue(trackPointNode, "AltitudeMeters")
        # heartRate
        self.heartrate = getNestedIntValue(trackPointNode, "HeartRateBpm", "Value")
        # cadence
        self.cadence = getIntValue(trackPointNode, "Cadence")
        # SensorPresent
        self.sensorPresent = getBoolValue(
            trackPointNode, "SensorState", "Present")

    def __str__(self):
        return "Distance: {} (Velocity: {} Time: {})\n".format(self.distance, self.velocity, str(self.time))

    def distanceTo(self, other):
        return other.distance - self.distance

    def timeTo(self, other):
        return (other.time - self.time).total_seconds()

    def to_pb2(self):
        tp = tcx_pb2.TrackPoint()
        tp.distanceMeters = self.distance
        tp.time = int(time.mktime(self.time.timetuple()))
        tp.position.latitudeDegrees = self.latitude
        tp.position.longitudeDegrees = self.longitude
        tp.altitudeMeters = self.altitude
        tp.cadence = self.cadence
        tp.sensorPresent = self.sensorPresent
        return tp


class Track:
    def __init__(self, trackNode=None):
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

    def to_pb2(self):
        track = tcx_pb2.Track()
        track.trackpoint.extend(
            list(map(lambda tp: tp.to_pb2(), self.trackpoints)))
        return track


class Lap:
    def __init__(self, lapNode=None):
        self.tracks = []
        self.totalTimeSeconds = 0.0
        self.distanceMeters = 0.0
        self.maximumSpeed = 0.0
        self.calories = 0.0
        self.averageHeartRateBPM = 0
        self.maximumHeartRateBPM = 0
        self.intensityActive = False
        self.cadence = 0
        self.triggerMethod = "Manual"
        self.notes = ""
        self.startTime = None
        if (lapNode == None):
            return
        self.sport = dateutil.parser.parse(lapNode.attributes["StartTime"].nodeValue)
        self.totalTimeSeconds = getFloatValue(lapNode, "TotalTimeSeconds")
        self.distanceMeters = getFloatValue(lapNode, "DistanceMeters")
        self.maximumSpeed = getFloatValue(lapNode, "MaximumSpeed")
        self.calories = getIntValue(lapNode, "Calories")
        self.averageHeartRateBPM = getNestedIntValue(
            lapNode, "AverageHeartRateBpm", "Value")
        self.maximumHeartRateBPM = getNestedIntValue(
            lapNode, "MaximumHeartRateBpm", "Value")
        self.intensityActive = getBoolValue(lapNode, "Intensity", "Active")
        self.cadence = getIntValue(lapNode, "Cadence")
        self.triggerMethod = getStringValue(lapNode, "TriggerMethod")
        self.notes = getStringValue(lapNode, "Notes")

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

    def to_pb2(self):
        lap = tcx_pb2.ActivityLap()
        lap.track.extend(list(map(lambda t: t.to_pb2(), self.tracks)))
        lap.totalTimeSeconds = self.totalTimeSeconds
        lap.distanceMeters = self.distanceMeters
        lap.maximumSpeed = self.maximumSpeed
        lap.calories = self.calories
        lap.averageHeartRateBPM = self.averageHeartRateBPM
        lap.maximumHeartRateBPM = self.maximumHeartRateBPM
        lap.intensityActive = self.intensityActive
        lap.cadence = self.cadence
        lap.notes = self.notes
        tmMap = {"Manual": tcx_pb2.ActivityLap.MANUAL,
                 "Distance": tcx_pb2.ActivityLap.DISTANCE,
                 "Location": tcx_pb2.ActivityLap.LOCATION,
                 "Time": tcx_pb2.ActivityLap.TIME,
                 "HeartRate": tcx_pb2.ActivityLap.HEARTRATE
                 }
        lap.triggerMethod = tmMap[self.triggerMethod]
        return lap


class Activity:
    span_distances = [400, 1000, 2000, 3000,
                      5000, 10000, 20000, 21097.5, 42193]

    def __init__(self, activityNode=None):
        self.sport = "Running"
        self.laps = []
        self.bestSpans = []
        self.id = None
        self.notes = ""
        self.training = None
        self.creator = ""
        if (activityNode == None):
            return
        self.sport = activityNode.attributes["Sport"].nodeValue
        for activityChild in activityNode.childNodes:
            if (activityChild.nodeName != "Lap"):
                continue
            lap = Lap(activityChild)
            self.laps.append(lap)
        self.id = getTimeValue(activityNode, "Id")
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
        if len(allTp) < 1:
            return best_time
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

    def to_pb2(self):
        act = tcx_pb2.Activity()
        act.lap.extend(list(map(lambda l: l.to_pb2(), self.laps)))
        return act


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

    def to_pb2(self):
        tcd = tcx_pb2.TrainingCenterDatabase()
        tcd.activities.activity.extend(
            list(map(lambda a: a.to_pb2(), self.activities)))
        return tcd


#tcd = TrainingCenterDatabase(
#    './tcxdata/2019-05-28T11_45_53.000Z_3528649242.tcx')

#tcd_proto = tcd.to_pb2()
#f = open("tcx.pb", "wb")
#f.write(tcd_proto.SerializeToString())
#f.close()

#print(tcd)

tcx_files = glob.glob('./tcxdata/*.tcx')
if not os.path.exists('pbdata'):
    os.makedirs('pbdata')
for file_name in tcx_files:
    base_name = os.path.basename(file_name)
    root, ext = os.path.splitext(base_name)
    print(file_name)
    tcd = TrainingCenterDatabase(file_name)
    f = open("pbdata/{}.pb".format(root), "wb")
    f.write(tcd.to_pb2().SerializeToString())
    f.close()
