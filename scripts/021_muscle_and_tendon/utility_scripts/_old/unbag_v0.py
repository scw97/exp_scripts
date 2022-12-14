#! /usr/bin/python
"""
Code to take the raw bag files output in Thad/Alyshas's rig, extract relevant data, and save to external source

Adapted from Thad's "unbag.py" and Francesca's "bag2hdf5.py"

TO DO:
    - left and right reference frame distinction
    - compression for image files?
"""
import sys, cv2, os, rosbag, h5py, cPickle
#
import numpy as np
import fnmatch
# coding: utf-8

################################################################################################
########################### GENERAL CONSTANTS ##################################################
################################################################################################
FLY_DB_PATH = '/media/imager/DataExternal/FlyDB'
# FLY_DB_PATH = '/media/sam/FlyDataE/FlyDB'

################################################################################################
########################### DEFINE CONVERTER CLASS #############################################
################################################################################################
class BagToHDF5:
    # ----------------------------------------------------------------------
    def __init__(self, fly_db_path=FLY_DB_PATH):
        """
        intialization function
        """
        # read in vars
        self.fly_db_path = fly_db_path

        # set placeholders for current bag/hdf5 files
        self.h5f = None
        self.inbag = None
        self.fly_num = None
        self.fly_path = None

        # other misc. vars that we might want to edit
        self.fly_folder_str = 'Fly%04d'

        self.kinefly_topic_names = ['/kinefly/flystate']
        self.led_panel_topic_names = ['/ledpanels/command']
        self.daq_phidget_topic_names = ['/phidgets_daq/all_data']
        self.cam_topic_names = ['/ca_camera_left/image_raw',
                                '/ca_camera_right/image_raw',
                                '/kine_camera_1/image_raw/compressed']
        self.exp_msg_topic_names = ['/exp_scripts/exp_state',
                                      '/exp_scripts/exp_state']
        self.metadata_topic_names = ['/exp_scripts/exp_metadata']
        self.rframe_topic_names = ['/LogRefFrame']
        self.unmixer_topic_names =  ['/unmixer_left/b1',
                                     '/unmixer_left/b2',
                                     '/unmixer_left/b3',
                                     '/unmixer_left/bkg',
                                     '/unmixer_left/hg1',
                                     '/unmixer_left/hg2',
                                     '/unmixer_left/hg3',
                                     '/unmixer_left/hg4',
                                     '/unmixer_left/i1',
                                     '/unmixer_left/i2',
                                     '/unmixer_left/iii1',
                                     '/unmixer_left/iii24',
                                     '/unmixer_left/iii3',
                                     '/unmixer_left/nm',
                                     '/unmixer_left/pr',
                                     '/unmixer_left/tpd',
                                     '/unmixer_right/b1',
                                     '/unmixer_right/b2',
                                     '/unmixer_right/b3',
                                     '/unmixer_right/bkg',
                                     '/unmixer_right/hg1',
                                     '/unmixer_right/hg2',
                                     '/unmixer_right/hg3',
                                     '/unmixer_right/hg4',
                                     '/unmixer_right/i1',
                                     '/unmixer_right/i2',
                                     '/unmixer_right/iii1',
                                     '/unmixer_right/iii24',
                                     '/unmixer_right/iii3',
                                     '/unmixer_right/nm',
                                     '/unmixer_right/pr',
                                     '/unmixer_right/tpd',
                                     ]

    # ----------------------------------------------------------------------
    def set_fly_num(self, fly_num):
        """
        function to set the input fly_num as the file we're focusing on
        """
        # write current fly number to self
        self.fly_num = fly_num

        # get corresponding bag and hdf5 filenames
        self.fly_path = os.path.normpath(os.path.join(self.fly_db_path, self.fly_folder_str % fly_num))
        if not os.path.exists(self.fly_path):
            self.fly_num = None
            self.fly_path = None
            print('Could not locate data for fly number %04d -- quitting' %(fly_num))
            return

        bagfile = None

        # taken from Thad's code -- I guess just being thorough about getting the right filename?
        if not (type(bagfile) is str):
            file_list = [f for f in os.listdir(self.fly_path) if f.endswith('.bag')]
            if (type(bagfile) is int):
                bagfile_name = file_list[bagfile]
            else:
                bagfile_name = file_list[0]
        else:
            bagfile_name = bagfile

        # load bag file
        bag_path = os.path.normpath(os.path.join(self.fly_path, bagfile_name))
        self.inbag = rosbag.Bag(bag_path)

        # get corresponding hdf5 path
        h5_fn = 'converted_' + bagfile_name[:-4] + '.hdf5'
        h5_path = os.path.normpath(os.path.join(self.fly_path, h5_fn))
        self.h5f = h5_path

        print('Now converting Fly%04d' % self.fly_num)

    # ----------------------------------------------------------------------
    def read_kinefly_data(self, topic_name):
        """
        read Kinefly data

        """
        # make sure we have a valid fly number entered
        if not self.fly_num:
            print('No valid fly number -- stopping')
            return

        # read various Kinefly messages from bag file
        tstamps = [msg[1].header.stamp.to_time() for msg in self.inbag.read_messages(topics=topic_name)
                   if len(msg[1].left.angles) > 0 and len(msg[1].right.angles) > 0]
        seq = [msg[1].header.seq for msg in self.inbag.read_messages(topics=topic_name)
               if len(msg[1].left.angles) > 0 and len(msg[1].right.angles) > 0]
        langles = [msg[1].left.angles[0] for msg in self.inbag.read_messages(topics=topic_name)
                   if len(msg[1].left.angles) > 0 and len(msg[1].right.angles) > 0]
        lgradients = [msg[1].left.gradients[0] for msg in self.inbag.read_messages(topics=topic_name)
                      if len(msg[1].left.angles) > 0 and len(msg[1].right.angles) > 0]
        lintensity = [msg[1].left.intensity for msg in self.inbag.read_messages(topics=topic_name)
                      if len(msg[1].left.angles) > 0 and len(msg[1].right.angles) > 0]
        rangles = [msg[1].right.angles[0] for msg in self.inbag.read_messages(topics=topic_name)
                   if len(msg[1].left.angles) > 0 and len(msg[1].right.angles) > 0]
        rgradients = [msg[1].right.gradients[0] for msg in self.inbag.read_messages(topics=topic_name)
                      if len(msg[1].left.angles) > 0 and len(msg[1].right.angles) > 0]
        rintensity = [msg[1].right.intensity for msg in self.inbag.read_messages(topics=topic_name)
                      if len(msg[1].left.angles) > 0 and len(msg[1].right.angles) > 0]
        # count=        [msg[1].count                  for msg in self.inbag.read_messages(topics=topic_name) if len(msg[1].left.angles)>0 and len(msg[1].right.angles)>0]
        try:
            hangles = [msg[1].head.angles[0] for msg in self.inbag.read_messages(topics=topic_name)
                       if len(msg[1].left.angles) > 0 and len(msg[1].right.angles) > 0]
        except:
            pass

        # write bag file messages to hdf5
        print('writing kinefly data for Fly%04d to hdf5' % (self.fly_num))
        with h5py.File(self.h5f, 'w') as h5f:
            h5f.create_dataset('flystate_tstamps', data=tstamps)
            h5f.create_dataset('flystate_seq', data=seq)
            h5f.create_dataset('flystate_langles', data=langles)
            h5f.create_dataset('flystate_lgrandients', data=lgradients)
            h5f.create_dataset('flystate_lintensity', data=lintensity)
            h5f.create_dataset('flystate_rangles', data=rangles)
            h5f.create_dataset('flystate_rgradients', data=rgradients)
            h5f.create_dataset('flystate_rintensity', data=rintensity)
            # h5f.create_dataset('flystate_count',data=count)
            try:
                h5f.create_dataset('flystate_hangles', data=hangles)
            except:
                pass

    # ----------------------------------------------------------------------
    def read_ledpanels_data(self, topic_name):
        """
        read led panel data

        """
        # make sure we have a valid fly number entered
        if not self.fly_num:
            print('No valid fly number -- stopping')
            return

        # read various LED panelmessages from bag file
        ros_tstamps = [msg[2].to_time() for msg in self.inbag.read_messages(topics=topic_name)]
        panels_command = [msg[1].command for msg in self.inbag.read_messages(topics=topic_name)]
        panels_arg1 = [msg[1].arg1 for msg in self.inbag.read_messages(topics=topic_name)]
        panels_arg2 = [msg[1].arg2 for msg in self.inbag.read_messages(topics=topic_name)]
        panels_arg3 = [msg[1].arg3 for msg in self.inbag.read_messages(topics=topic_name)]
        panels_arg4 = [msg[1].arg4 for msg in self.inbag.read_messages(topics=topic_name)]
        panels_arg5 = [msg[1].arg5 for msg in self.inbag.read_messages(topics=topic_name)]
        panels_arg6 = [msg[1].arg6 for msg in self.inbag.read_messages(topics=topic_name)]

        # write LED panel data to hdf5
        print('writing LED panel data for Fly%04d to hdf5' % (self.fly_num))
        with h5py.File(self.h5f, 'w') as h5f:
            h5f.create_dataset('ledpanels_ros_tstamps', data=ros_tstamps)
            h5f.create_dataset('ledpanels_panels_command', data=panels_command)
            h5f.create_dataset('ledpanels_panels_arg1', data=panels_arg1)
            h5f.create_dataset('ledpanels_panels_arg2', data=panels_arg2)
            h5f.create_dataset('ledpanels_panels_arg3', data=panels_arg3)
            h5f.create_dataset('ledpanels_panels_arg4', data=panels_arg4)
            h5f.create_dataset('ledpanels_panels_arg5', data=panels_arg5)
            h5f.create_dataset('ledpanels_panels_arg6', data=panels_arg6)

    # ----------------------------------------------------------------------
    def read_muscle_unmixer_data(self, topic_name):
        """
        read muscle unmixer data

        """
        # make sure we have a valid fly number entered
        if not self.fly_num:
            print('No valid fly number -- stopping')
            return

        # read a given muscle unmixer message from bag file
        ros_tstamps = [msg[2].to_time() for msg in self.inbag.read_messages(topics=topic_name)]
        tstamps = [msg[1].header.stamp.to_time() for msg in self.inbag.read_messages(topics=topic_name)]
        seq = [msg[1].header.seq for msg in self.inbag.read_messages(topics=topic_name)]
        value = [msg[1].value for msg in self.inbag.read_messages(topics=topic_name)]
        muscle = [msg[1].muscle for msg in self.inbag.read_messages(topics=topic_name)]

        # write muscle messages to hdf5
        print('writing %s muscle unmixer data for Fly%04d to hdf5' % (topic_name, self.fly_num))
        with h5py.File(self.h5f, 'w') as h5f:
            h5f.create_dataset(str(topic_name[1:]) + '/muscleunmixer_ros_tstamps', data=ros_tstamps)
            h5f.create_dataset(str(topic_name[1:]) + '/muscleunmixer_tstamps', data=tstamps)
            h5f.create_dataset(str(topic_name[1:]) + '/muscleunmixer_seq', data=seq)
            h5f.create_dataset(str(topic_name[1:]) + '/muscleunmixer_value', data=value)
            h5f.create_dataset(str(topic_name[1:]) + '/muscleunmixer_muscle', data=muscle)

    # ----------------------------------------------------------------------
    def read_muscle_unmixer_data_all(self):
        """
        read ALL muscle unmixer data

        """
        for topic_name in self.unmixer_topic_names:
            self.read_muscle_unmixer_data(topic_name)

    # ----------------------------------------------------------------------
    def read_daq_phidget_data(self, topic_name):
        """
        read daq phidget data

        """
        # make sure we have a valid fly number entered
        if not self.fly_num:
            print('No valid fly number -- stopping')
            return

        # read DAQ messages
        ros_tstamps = [msg[2].to_time() for msg in self.inbag.read_messages(topics=topic_name)]
        time = [msg[1].time for msg in self.inbag.read_messages(topics=topic_name)]
        channels = [msg[1].channels for msg in self.inbag.read_messages(topics=topic_name)]
        values = [msg[1].values for msg in self.inbag.read_messages(topics=topic_name)]

        # write DAQ messages to hdf5
        print('writing DAQ phidget data for Fly%04d to hdf5' % (self.fly_num))
        with h5py.File(self.h5f, 'w') as h5f:
            h5f.create_dataset('daq_ros_tstamps', data=ros_tstamps)
            h5f.create_dataset('daq_time', data=time)
            h5f.create_dataset('daq_channels', data=channels)
            h5f.create_dataset('daq_value', data=values)
    
    # ----------------------------------------------------------------------
    def read_general_msg_data(self, topic_name):
        """
        read messages like exp_state and exp_block

        """
        # make sure we have a valid fly number entered
        if not self.fly_num:
            print('No valid fly number -- stopping')
            return

        # read string messages
        ros_tstamps = [msg[2].to_time() for msg in self.inbag.read_messages(topics=topic_name)]
        msg_data = [msg[1].data for msg in self.inbag.read_messages(topics=topic_name)]

        # write DAQ messages to hdf5
        print('writing %s data for Fly%04d to hdf5' % (topic_name, self.fly_num))
        with h5py.File(self.h5f, 'w') as h5f:
            h5f.create_dataset(str(topic_name[1:]) + '/ros_tstamps', data=ros_tstamps)
            h5f.create_dataset(str(topic_name[1:]) + '/msgs', data=msg_data)
            # h5f.create_dataset(str(topic_name[1:]) + '/msgs', data=np.array(msg_data,dtype = 'S256'))

    # ----------------------------------------------------------------------
    def read_metadata(self, mtd_topic_name='/exp_scripts/exp_metadata'):
        """
        read experiment metadata. NB: this should be a little different than the above
         NB: currently writing to txt files but should probably add this info to hdf5 file as well...

        """
        # make sure we have a valid fly number entered
        if not self.fly_num:
            print('No valid fly number -- stopping')
            return

        # read metadata messages
        metadata_msgs = [(topic, msg, t) for topic, msg, t in self.inbag.read_messages(topics=mtd_topic_name)]

        # unpickle metadata and read out entries
        mtd = cPickle.loads(str(metadata_msgs[0][1].data))
        git_sha = mtd['git_SHA']
        exp_description = mtd['exp_description']
        fly_genotype = mtd['fly_genotype']
        genotype_nickname = mtd['genotype_nickname']
        script_code = mtd['script_code']

        # also get fly DOB
        import datetime
        import yaml
        info_dict = yaml.load(self.inbag._get_yaml_info())
        dtm = datetime.datetime.fromtimestamp(info_dict['start'])
        m, d, y = mtd['fly_dob'].split('.')  ##'8.13.2017'.split('.')
        dob_dt = datetime.datetime(year=int(y), month=int(m), day=int(d))
        delta_dt = dtm - dob_dt

        # write entries to text files
        with open(os.path.join(self.fly_path, 'git_SHA.txt'), 'wt') as f:
            f.write(git_sha)
        sp = os.path.split(mtd['script_path'])[-1]
        with open(os.path.join(self.fly_path, sp), 'wt') as f:
            f.write(script_code)
        with open(os.path.join(self.fly_path, 'exp_description.txt'), 'wt') as f:
            f.write(exp_description)
        with open(os.path.join(self.fly_path, 'fly_genotype.txt'), 'wt') as f:
            f.write(fly_genotype)
        with open(os.path.join(self.fly_path, 'genotype_nickname.txt'), 'wt') as f:
            f.write(genotype_nickname)
        with open(os.path.join(self.fly_path, 'age.txt'), 'wt') as f:
            f.write(str(delta_dt))

    # --------------------------------------------------------------------------------
    def read_cam_data(self, topic_name):
        """
        read cam images.
        NB: these are saved to separate hdf5 files, as in Thad's code

        """
        # make sure we have a valid fly number entered
        if not self.fly_num:
            print('No valid fly number -- stopping')
            return

        # read camera messages
        ros_tstamps = [msg[2].to_time() for msg in self.inbag.read_messages(topics=topic_name)]
        tstamps = [msg[1].header.stamp.to_time() for msg in self.inbag.read_messages(topics=topic_name)]
        img_msgs = [msg[1] for msg in self.inbag.read_messages(topics=topic_name)]

        # convert images (the method for ROS msg -> cv2 image depends on the camera)
        if "compressed" in topic_name:
            imgs = [cv2.imdecode(np.fromstring(imm.data, np.uint8), cv2.IMREAD_GRAYSCALE) for imm in img_msgs]

        else:
            from cv_bridge import CvBridge, CvBridgeError
            cv_bridge = CvBridge()
            imgs = [cv_bridge.imgmsg_to_cv2(imm) for imm in img_msgs]

        # write everything to SEPARATE hdf5
        save_name = [s for s in topic_name.split('/') if not s == ""][0] + '.hdf5'
        save_path = os.path.normpath(os.path.join(self.fly_path, save_name))

        print('writing %s cam data for Fly%04d to hdf5' % (save_name, self.fly_num))
        with h5py.File(save_path, 'w') as h5f:
            h5f.create_dataset('cam_ros_tstamps', data=ros_tstamps)
            h5f.create_dataset('cam_tstamps', data=tstamps)
            h5f.create_dataset('cam_imgs', data=np.asarray(imgs), compression="gzip")
    

    # --------------------------------------------------------------------------------
    def read_rframe_data(self, topic_name):
        """
        read reference frames that are hopefully logged from experiments

        """
        # make sure we have a valid fly number entered
        if not self.fly_num:
            print('No valid fly number -- stopping')
            return

        # read various LED panelmessages from bag file
        ros_tstamps = [msg[2].to_time() for msg in self.inbag.read_messages(topics=topic_name)]
        ref_frame_components = [msg[1].components for msg in self.inbag.read_messages(topics=topic_name)]
        ref_frame_p = [msg[1].p.data for msg in self.inbag.read_messages(topics=topic_name)]
        ref_frame_a1 = [msg[1].a1.data for msg in self.inbag.read_messages(topics=topic_name)]
        ref_frame_a2 = [msg[1].a2.data for msg in self.inbag.read_messages(topics=topic_name)]
        ref_frame_A = [msg[1].A.data for msg in self.inbag.read_messages(topics=topic_name)]
        ref_frame_A_inv = [msg[1].A_inv.data for msg in self.inbag.read_messages(topics=topic_name)]
        
        # write reference frame data o SEPARATE hdf5
        # *** NB: need to update this to save left and right side, eventually
        save_name = [s for s in topic_name.split('/') if not s == ""][0] + '.hdf5'
        save_path = os.path.normpath(os.path.join(self.fly_path, save_name))
        
        print('writing reference frame data for Fly%04d to hdf5' % (self.fly_num))
        with h5py.File(save_path, 'w') as h5f:
            h5f.create_dataset('rframe_ros_tstamps', data=ros_tstamps)
            h5f.create_dataset('ref_frame_components', data=ref_frame_components)
            h5f.create_dataset('ref_frame_p', data=np.array(ref_frame_p))
            h5f.create_dataset('ref_frame_a1', data=np.array(ref_frame_a1))
            h5f.create_dataset('ref_frame_a2', data=np.array(ref_frame_a2))
            h5f.create_dataset('ref_frame_A', data=np.array(ref_frame_A))
            h5f.create_dataset('ref_frame_A_inv', data=np.array(ref_frame_A_inv))
      
    # --------------------------------------------------------------------------------
    def do_conversion_all(self):
        """
        function to execute the various read/write functions for a given file
        NB: can edit as needed/demands for different data types change
        """
        # read/write camera data. NB: this will be to separate files
        for topic in self.cam_topic_names:
            self.read_cam_data(topic)
           
        # read/write muscle reference frame info
        for topic in self.rframe_topic_names:
            self.read_rframe_data(topic)

        # read/write kinefly data
        for topic in self.kinefly_topic_names:
            self.read_kinefly_data(topic)

        # read/write led panel data
        for topic in self.led_panel_topic_names:
            self.read_ledpanels_data(topic)

        # read/write daq phidget data
        for topic in self.daq_phidget_topic_names:
            self.read_daq_phidget_data(topic)
        
        # read/write experiment 'state' messages like 'exp_state' and 'exp_block'
        for topic in self.exp_msg_topic_names:
            self.read_general_msg_data(topic)

        # read/write muscle data
        for topic in self.unmixer_topic_names:
            self.read_muscle_unmixer_data(topic)
        
        # read/write metadata. NB: this will be to separate files
        for topic in self.metadata_topic_names:
           self.read_metadata(mtd_topic_name=topic)

        


################################################################################################
########################### RUN SCRIPT #########################################################
################################################################################################
if __name__ == '__main__':
    # read in flies from terminal input
    flies = [int(x) for x in sys.argv[1:]]
    # flies = [2]

    # create instance of converter object
    myBagToHDF5 = BagToHDF5(fly_db_path=FLY_DB_PATH)

    # read out all data for each fly
    for fly in flies:
        # make sure we're looking at current fly
        myBagToHDF5.set_fly_num(fly)

        # grab data out
        myBagToHDF5.do_conversion_all()
