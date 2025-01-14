"""People Counter."""
"""
 Copyright (c) 2018 Intel Corporation.
 Permission is hereby granted, free of charge, to any person obtaining
 a copy of this software and associated documentation files (the
 "Software"), to deal in the Software without restriction, including
 without limitation the rights to use, copy, modify, merge, publish,
 distribute, sublicense, and/or sell copies of the Software, and to
 permit person to whom the Software is furnished to do so, subject to
 the following conditions:
 The above copyright notice and this permission notice shall be
 included in all copies or substantial portions of the Software.
 THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
 EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
 MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
 NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
 LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
 OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
 WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""


import os
import sys
import time
import socket
import json
import cv2
import numpy as np
import logging as log
import paho.mqtt.client as mqtt
from random import randint
from argparse import ArgumentParser
from inference_v1 import Network

CLASSES = ['person']
CPU_EXTENSION = "/opt/intel/openvino/deployment_tools/inference_engine/lib/intel64/libcpu_extension_sse4.so"


# MQTT server environment variables
HOSTNAME = socket.gethostname()
IPADDRESS = socket.gethostbyname(HOSTNAME)
MQTT_HOST = IPADDRESS
MQTT_PORT = 3001
MQTT_KEEPALIVE_INTERVAL = 60


def build_argparser():
    """
    Parse command line arguments.

    :return: command line arguments
    """
    parser = ArgumentParser()
    parser.add_argument("-m", "--model", required=True, type=str,
                        help="Path to an xml file with a trained model.")
    parser.add_argument("-i", "--input", required=True, type=str,
                        help="Path to image or video file")
    parser.add_argument("-l", "--cpu_extension", required=False, type=str,
                        default=None,
                        help="MKLDNN (CPU)-targeted custom layers."
                             "Absolute path to a shared library with the"
                             "kernels impl.")
    parser.add_argument("-d", "--device", type=str, default="CPU",
                        help="Specify the target device to infer on: "
                             "CPU, GPU, FPGA or MYRIAD is acceptable. Sample "
                             "will look for a suitable plugin for device "
                             "specified (CPU by default)")
    parser.add_argument("-pt", "--prob_threshold", type=float, default=0.5,
                        help="Probability threshold for detections filtering"
                        "(0.5 by default)")
    args = parser.parse_args()
    
    return args


def connect_mqtt():
    ### TODO: Connect to the MQTT client ###
    client = mqtt.Client()
    client.connect(MQTT_HOST, MQTT_PORT, MQTT_KEEPALIVE_INTERVAL)
    return client

def get_class_names(class_nums):
    class_names= []
    for i in class_nums:
        class_names.append(CLASSES[int(i)])
    return class_names

def draw_boxes(frame, result, args, width, height):
    '''
    Draw bounding boxes onto the frame.
    '''
    counter = 0
    for box in result[0][0]: # Output shape is 1x1x100x7
        conf = box[2]
        obj = box[1] # OBJECT = 1 ie. person ( for coco dataset)
        #if conf >= 0.5:
        if conf >= 0.2 and obj == 1:
            counter += 1
            xmin = int(box[3] * width)
            ymin = int(box[4] * height)
            xmax = int(box[5] * width)
            ymax = int(box[6] * height)
            cv2.rectangle(frame, (xmin, ymin), (xmax, ymax), (0, 225, 0), 1)
        #frame = cv2.putText(frame, "No of PEOPLE = "+str(counter), (5, 15), cv2.FONT_HERSHEY_COMPLEX_SMALL,  0.8, (0, 255, 0), 1, cv2.LINE_AA)
        #frame = cv2.resize(frame, (width,height))
    return frame,counter

def infer_on_stream(args, client):
    """
    Initialize the inference network, stream video to network,
    and output stats and video.

    :param args: Command line arguments parsed by `build_argparser()`
    :param client: MQTT client
    :return: None
    """
    # Initialise the class
    plugin = Network()
    # Set Probability threshold for detections
    prob_threshold = args.prob_threshold

    ### TODO: Load the model through `infer_network` ###
    plugin.load_model(args.model, args.device, CPU_EXTENSION)
    net_input_shape = plugin.get_input_shape()

    ### TODO: Handle the input stream ###
    cap = cv2.VideoCapture(args.input)
    cap.open(args.input)
    width = int(cap.get(3))
    height = int(cap.get(4))
    last_count= 0
    total_count = 0
    ### TODO: Loop until stream is over ###
    while cap.isOpened():

        ### TODO: Read from the video capture ###
        flag, frame = cap.read()
        if not flag:
            break
        key_pressed = cv2.waitKey(60)

        ### TODO: Pre-process the image as needed ###
        
        p_frame = cv2.resize(frame, (net_input_shape[3], net_input_shape[2]))
        #p_frame = cv2.resize(frame, (300,300))
        p_frame_1 = p_frame
        p_frame = p_frame.transpose((2,0,1))
        p_frame = p_frame.reshape(1, *p_frame.shape)
       
        
        

        ### TODO: Start asynchronous inference for specified request ###
        plugin.exec_net(p_frame)

        ### TODO: Wait for the result ###
        if plugin.wait() == 0:

            ### TODO: Get the results of the inference request ###
            result = plugin.get_output()
            
            
            ### TODO: Extract any desired stats from the results ###
            #out_frame, count = draw_boxes(p_frame_1, result, args, width, height)
            out_frame, current_count = draw_boxes(p_frame_1, result, args, net_input_shape[3], net_input_shape[2])
            #np.ascontiguousarray(out_frame, dtype=np.float32)
            
            #out_frame = cv2.resize(out_frame,(width,height))
            out_frame = out_frame.copy(order='C')
            out_frame = cv2.resize(out_frame, (width,height))
            out_frame = cv2.putText(out_frame, "No of PEOPLE = "+str(current_count), (5, 15), cv2.FONT_HERSHEY_COMPLEX_SMALL,  0.8, (0, 255, 0), 1, cv2.LINE_AA)
            
            
            ### TODO: Calculate and send relevant information on ###
            #class_names = get_class_names(classes)
            #speed = randint(50,70)
            #client.publish("class", json.dumps({"class_names": class_names}))
            #client.publish("speedometer", json.dumps({"speed": speed}))
            #client.publish("person", json.dumps({"currentCount": count}))
            #client.publish("person", json.dumps({"count": current_count, "total":1}))
            ### current_count, total_count and duration to the MQTT server ###
            ### Topic "person": keys of "count" and "total" ###
            ### Topic "person/duration": key of "duration" ###
            # When new person enters the video
            
            if current_count > last_count:
                start_time = time.time()
                last_count +=1
                total_count = total_count + current_count - last_count
                client.publish("person", json.dumps({"total": total_count}))
            # Person duration in the video is calculated
            if current_count < last_count:
                duration = int(time.time() - start_time)
                # Publish messages to the MQTT server
                client.publish("person/duration",json.dumps({"duration": duration}))
            client.publish("person", json.dumps({"count": current_count, "total":total_count}))
            last_count = current_count

        ### TODO: Send the frame to the FFMPEG server ###
        
        sys.stdout.buffer.write(out_frame)
        sys.stdout.flush()
        if key_pressed == 27:
            break

        ### TODO: Write an output image if `single_image_mode` ###

       
    # Release the capture and destroy any OpenCV windows
    cap.release()
    cv2.destroyAllWindows()
    
    ### TODO: Disconnect from MQTT
    client.disconnect()
    
        


def main():
    """
    Load the network and parse the output.

    :return: None
    """
    # Grab command line args
    args = build_argparser()
    # Connect to the MQTT server
    client = connect_mqtt()
    # Perform inference on the input stream
    infer_on_stream(args, client)


if __name__ == '__main__':
    main()
