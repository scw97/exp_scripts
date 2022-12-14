#!/usr/bin/env python

import time
import os
import sys
import roslib
import rospy
import rostopic
import readline
import cPickle
import itertools
import yaml
import copy
import numpy as np
from std_msgs.msg import String
from exp_scripts.msg import MsgExpState
from exp_scripts.msg import MsgExpMetadata
from exp_scripts import git_tools
from ledpanels import display_ctrl
from muscle_imager.srv import SrvRefFrame
from muscle_imager.srv import SrvRefFrameRequest
from scw_panel_lib import turn_off_panels, exc_visual_stim

""" MAKE SURE THIS IS EXECUTABLE; USE 'chmod +x mypythonscript.py' in terminal """
############################################################################
########################### Metadata Information ###########################
############################################################################

exp_description = \
""" Simultaneous imaging of muscle activity and tendon movement ---

Testing to see if I can image both calcium activity in muscles AND tendon movement

NB: While happending in the same fly, the muscles and tendons are being imaged on separate sides

Legs cut off; head NOT fixed (for now)

In this particular experiment paradigm, looking at flight start and stop

Testing flies without GCaMP expression in the muscle but hopefully a brighter fluorophore in the tendons
"""

fly_dob = '12.11.2022'

fly_genotype = """w[1118]/w[*] ; 10XUAS-IVS-mCD8::RFP/+ ; sr[md710]/+"""
genotype_nickname = 'G84/RFP'

# fly_genotype = """w[1118]/+[HCS] ; +/(GMR39E01-LexA,GCaMP7f-LexOp) ; +/(sr[md710],UAS-tdTom.S)"""
# genotype_nickname = 'hinge_and_muscle/HCS'

head_fixed = False 
legs_cut = True

print genotype_nickname


############################################################################
########################### Script Variables ##########################
############################################################################

#Stimulus periods
CONDITION_DURATION = 20.0

# how many trials per run
NUM_REPS = 5

#pattern playback rate 240 positions for 360deg
CL_GAIN_X = -2  # closed loop gain(?). alysha had it set up to -1; Francesca to 3

# string for visual stimulus
PATTERN_NAME = 'Pattern_bar.mat'

# name of unmixer being used (Thad's or Johan's)
UNMIXER_NAME = 'unmixer'  # 'unmixer' or 'live_viewer' 
############################################################################
########################### Initialize Experiment ##########################
############################################################################

script_path = os.path.realpath(sys.argv[0])
script_dir = os.path.dirname(script_path)

#load the script to publish as message
with open(script_path,'rt') as f:
    script_code = f.read() 

#list of all git tracked repositories
with open(os.path.join(script_dir,'tracked_git_repos.txt')) as f:
    repo_dirs = f.readlines() 

assert git_tools.check_git_status(repo_dirs)
git_SHA = git_tools.get_SHA_keys(repo_dirs)

# check if ROS is on yet
try:
    rostopic.get_topic_class('/rosout')
    is_rosmaster_running = True
except rostopic.ROSTopicIOException as err:
    is_rosmaster_running = False
    print(err)
    
#############################################################################
################################ Run experiment #############################
#############################################################################

if __name__ == '__main__':
    try:
        # ----------------------------------------------------------------------
        # create LED panel controller object
        print 'start'
        rospy.init_node('exp_script')
        exp_dir = script_dir
        ctrl = display_ctrl.LedControler()
        ctrl.load_SD_inf(exp_dir + '/firmware/panel_controller/SD.mat')
        
        # set up ROS publisher topics
        exp_pub = rospy.Publisher('/exp_scripts/exp_state', 
                                    String,
                                    queue_size = 10)
        meta_pub = rospy.Publisher('/exp_scripts/exp_metadata', 
                                    String,
                                    queue_size = 10)
        blk_pub = rospy.Publisher('/exp_scripts/exp_block',
                                    String,
                                    queue_size = 10)
        
        # ----------------------------------------------------------------------
        # get left and right reference frames
        # rospy.wait_for_service('/unmixer_left/RefFrameServer')  # OUT OF DATE -- using live_viewer_(side) now
        # rospy.wait_for_service('/unmixer_right/RefFrameServer')
        
        time.sleep(1) # wait for all the publishers to come online

        # ----------------------------------------------------------------------
        # save metadata
        try:
            get_ref_frame_left = rospy.ServiceProxy('/%s_left/RefFrameServer'%(UNMIXER_NAME), SrvRefFrame) 
            print(get_ref_frame_left())
            rospy.logwarn(get_ref_frame_left())
        except (rospy.service.ServiceException, rospy.ROSException), e:
            print 'LEFT camera not in use: %s'%(e)
            rospy.logwarn('LEFT camera not in use: %s'%(e))
            get_ref_frame_left = lambda *args, **kwargs: None

        try:
            get_ref_frame_right = rospy.ServiceProxy('/%s_right/RefFrameServer'%(UNMIXER_NAME), SrvRefFrame) 
            print(get_ref_frame_right())
            rospy.logwarn(get_ref_frame_right()) 
        except (rospy.service.ServiceException, rospy.ROSException), e:
            print 'RIGHT camera not in use: %s'%(e)
            rospy.logwarn('RIGHT camera not in use: %s'%(e))
            get_ref_frame_right = lambda *args, **kwargs: None

        metadata =   {'git_SHA':git_SHA,
                      'script_path':script_path,
                      'exp_description':exp_description,
                      'script_code':script_code,
                      'fly_dob':fly_dob,
                      'fly_genotype':fly_genotype,
                      'genotype_nickname':genotype_nickname,
                      'head_fixed':head_fixed}

        meta_pub.publish(cPickle.dumps(metadata))
        
        
        ###################################################################################
        # Run experiment
        ###################################################################################

        # get start time
        t0 = time.time()
        
        # stop panels 
        ctrl.stop()
        
        # start closed-loop stripe movement -- going to run this throughout
        ctrl.set_position_function_by_name('X', 'default')  # not sure what this does
        ctrl.set_pattern_by_name(PATTERN_NAME)  # set pattern 
        ctrl.set_position(0, 0)  # set initial position
        ctrl.set_mode('xrate=ch0','yrate=funcy')  # not really sure what this does
        ctrl.send_gain_bias(gain_x=CL_GAIN_X, gain_y=0, bias_x=0, bias_y=0) # set gain and bias for panel
    
        # execute panel motion
        ctrl.start()
        
        # publish the state
        exp_pub.publish('closed_loop;gain=%s'%(CL_GAIN_X))
        blk_pub.publish('stripe_fix')
        
        # pause a bit before printing commands
        time.sleep(5)

        # loop over repetitions
        for rep in range(NUM_REPS):
            # print a message to give an air puff (initiate flight), then allow flight for a bit
            rospy.logwarn('PUFF')
            time.sleep(CONDITION_DURATION)
            
            # print a message to stop with brush hair, then let fly be stopped for a bit
            rospy.logwarn('STOP')
            time.sleep(CONDITION_DURATION)
        

        #################################################
        # Wind down expt
        #################################################

        #publish a refrence frame as a status message to mark the end of the experiment.
        print(get_ref_frame_left())
        print(get_ref_frame_right())

        meta_pub.publish(cPickle.dumps(metadata))
        
        # print some stuff at the end to let us know we're done!
        rospy.logwarn('end_of_experiment')
        rospy.logwarn(time.time()-t0)
        
        # turn off panels
        turn_off_panels(ctrl)

    except rospy.ROSInterruptException:
        print ('exception')
        pass
