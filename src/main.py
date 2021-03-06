"""DSRC+Radar Collision Avoidance

This is the main application interface for the DSRC+Radar collision avoidance
application. The purpose of this application is to provide a demonstration as
to how the combined use of DSRC and Radar data can create more accurate model
of a vehicle's environment and ultimately lead to improved safety through
advanced collision avoidance software.

Usage:
    There are many external software and hardware requirements in order to
    correctly use this software in its current form. For details on those
    requirements please go to the README.md file in root of this repository.

    For details on how to use this application in particular please try running
    `python main.py -h` to display the help text.

Software Overview:
    This application is split into multiple parts in order to facilitate
    component swapping and reuse. An overview of each component is provided
    below.

    Main - Simple setup script for our application. It manages initializing our
    packages and parsing of some command line arguments.

    Collision - This package is included mainly for the purpose of demonstration.
    It takes the information provided by our Combiner and calculates any predicted
    collisions displaying warnings in a simple UI.

    Combiner - The Combiner package is where most of our core technology resides.
    This package is responsible for taking data from each source, normalizing the
    format, and combining that information into a single model of the car's
    environment. Once the combination is complete the new model gets passed to
    the registered callback function, which in our case feeds data into our collision
    avoidance system.

    DSRC - The DSRC package is split up into 3 main components. There are 2 parsers:
    the data parser which handles the UDP log packets written by the DSRC
    and the log parser which reads previously logged events and replays them in
    real time. The log parser is useful in application testing since it lets us
    recreate a sequence of events in our code that we previously recorded using
    the data parser in a real-world test. Sitting in front of both of these parsers
    is the dispatcher which instantiates the proper parser for the current environment
    and acts as a standard interface to the combiner, passing messages to the
    combiner as they are recieved.

    Radar - The structure in this package is quite similar to that in the DSRC
    package. Please read that section for details on the general architecture.
    Note that the Radar utilizes the Kvaser Canlib Python SDK in order to retrieve
    information from the CAN Bus about the radar.

    Logs - This directory stores logs which are produced during the application
    runtime. We also have archived several logs which include raw DSRC & Radar
    information from different real-world experiments for the purpose of testing
    our software's performance.

    Util - This is simply a package which holds all of the utility classes which
    we use throughout the codebase.

Authors:
    Bryce Arden
    Phillip Lemons
    Ryan Meek
    Jon Reynolds
    Kevin Rosen
    Robert Syvarth
"""
import time
import canlib
import logging
import argparse
from multiprocessing import Queue
import os

from combiner.combiner_base import Combiner
from collision.collision_avoid import CollisionAvoidance
from util.logger_conf import configure_logs

def main():
    """ Main application entry point. """
    args = parse_args()

    configure_logs(getattr(logging, args.log_level.upper(), None))
    print_header()

    if args.test_logger:
        test_logger()

    collision_avoid_queue = Queue()

    # Init the collision avoidance class
    if args.visualize_dir:
        collision_avoid = CollisionAvoidance(collision_avoid_queue, args.video_file, 
            int(args.export_interval), args.export_path)

        collision_avoid.start()

    # Setup the Combiner to call collision_avoid.new_data_handler every time new data is available!
    combiner = Combiner(collision_avoid_queue,
        args.log_dsrc, args.log_radar,
        args.dsrc_log_file, args.radar_log_file,
        args.dsrc_enabled, args.radar_enabled,
        args.log_level.upper(), args.log_config)

    # This is a blocking call, will keep on going while parsers are going for dsrc and radar
    combiner.start()

def parse_args():
    """ Evaluate commandline arguments passed to script. """
    parser = argparse.ArgumentParser()
    parser.add_argument('--no-log-dsrc',
                        dest='log_dsrc',
                        default=True,
                        action='store_false',
                        help="Disable dsrc logging (only affects live data)")
    parser.add_argument('--no-log-radar',
                        dest='log_radar',
                        default=True,
                        action='store_false',
                        help="Disable radar logging (only affect live data)")
    parser.add_argument('--test-logger',
                        dest='test_logger',
                        action='store_true',
                        help="Test the logging created by Bryce")
    parser.add_argument('--no-radar',
                        dest='radar_enabled',
                        action='store_false',
                        help="Disable radar data collection")
    parser.add_argument('--no-dsrc',
                        dest='dsrc_enabled',
                        action='store_false',
                        help="Disable dsrc data collection")
    parser.add_argument('--load-dsrc-log',
                        dest='dsrc_log_file',
                        help="Path to the dsrc log file to use for emulation \
                        (If not passed we use live data)")
    parser.add_argument('--load-radar-log',
                        dest='radar_log_file',
                        help="Path to the radar log file to use for emulation \
                        (If not passed we use live data)")
    parser.add_argument('--log',
                        dest='log_level',
                        default="DEBUG",
                        help="Set the level for the debug logger")
    parser.add_argument('--load-video',
                        dest='video_file',
                        help="Video file to draw over")
    parser.add_argument('--visualize',
                        dest='visualize_dir',
                        help="Path to directory to load all vizualization info from\
                        (equivalent of passing load-dsrc-log, load-radar-log, load-video)")
    parser.add_argument('--export_interval',
                        dest='export_interval',
                        default=1000,
                        help="Interval to take screenshots of output")
    parser.add_argument('--export_path',
                        dest='export_path',
                        help="Path to put screenshots in")


    args = parser.parse_args()

    if args.visualize_dir:
        args.dsrc_log_file = args.visualize_dir + '/dsrc.log'
        args.radar_log_file = args.visualize_dir + '/radar.log'
        args.video_file = args.visualize_dir + '/video.mp4'
        args.log_config = args.visualize_dir + '/config.json'

    if args.export_path and not os.path.exists(args.export_path):
            os.makedirs(args.export_path)

    return args

def print_header():
    """ Print out a fancy little header with some status info. """
    cl = canlib.canlib();
    channels = cl.getNumberOfChannels()
    logging.info("/-------------------------------------------------\\")
    logging.info("| Booting DSRC+Radar Collision Avoidance")
    logging.info("| Canlib running version %s with %s channels" % (cl.getVersion(), channels))
    logging.info("\-------------------------------------------------/\n")

def test_logger():
    """Test code that Bryce wrote to ensure logger was functioning"""
    logger = logging.getLogger('dsrc')
    logger.info("hello DSRC!")
    logger = logging.getLogger('radar')
    logger.info("hello radar!")
    logger = logging.getLogger('combined')
    logger.info("hello combined!")
    logger = logging.getLogger('debug')
    logger.debug("hello debug!")
    logger.warning("this should print to console")
    logger = logging.getLogger('debug_dsrc')
    logger.debug("hello debug_dsrc!")
    logger = logging.getLogger('debug_radar')
    logger.debug("hello debug_radar!")
    logger = logging.getLogger('debug_combined')
    logger.debug("hello debug_combined!")

if __name__ == "__main__":
    main()
