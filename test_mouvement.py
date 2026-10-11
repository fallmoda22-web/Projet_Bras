from robodk import robolink

RDK = robolink.Robolink()
robot = RDK.Item('ABB IRB 120-3/0.6', robolink.ITEM_TYPE_ROBOT)

pose = robot.Pose()
x, y, z = pose.Pos()
pose.setPos([x, y, z + 20])   # monte de 2 cm

print("IK possible :", len(robot.SolveIK(pose).list()) > 0)
robot.MoveL(pose)
print("Nouvelle pose :", robot.Pose().Pos())