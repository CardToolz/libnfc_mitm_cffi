import sys
import logging

import nfc_helper

logger = logging.getLogger(__name__)

# TODO: implement data hook as a class with a separate thing when the data is not found in a log
@nfc_helper.log_debug
def data_hook(direction, data, easy_framing):
    send_fragmented = False
    # logger.info(sys._getframe().f_code.co_name)
    # if len(data) > 100:
    if data[0] == 0xBA and data[1] == 0xAD:
        logger.info ("[+]Corrupt data")
        send_fragmented = True
        # TODO: send a mutated data here
        # data = prepare_apdu()

    # logger.info("frame direction: %s" % direction)
    # logger.info ("Data hook, send_fragmented: %s" % send_fragmented)
    logger.info("Frame direction {}, send_fragmented: {}".format(direction, send_fragmented))
    return send_fragmented, data
