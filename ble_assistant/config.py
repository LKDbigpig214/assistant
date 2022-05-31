#!/user/bin/env python3
"""
@author: qiudeliang

All rights reserved.
"""

import os
import logging
import json
from pathlib import Path
from typing import Dict, Any, Union, List

import yaml
from pydantic import (BaseSettings, validator, HttpUrl)


def dict_key_to_upper(src: Dict[str, Any]):
    """
    dict key to upper.
    :param src:
    :return:
    """
    res = {key.upper(): src[key] for key in src}
    return res


def json_config_setting_source(base_settings: BaseSettings) -> Dict[str, Any]:
    """
    json config.
    :param base_settings:
    :return:
    """
    encoding = base_settings.__config__.env_file_encoding
    case_sensitive = base_settings.__config__.case_sensitive
    with Path('ble_assistant.json') as f:
        if f.exists():
            res = json.loads(f.read_text(encoding))
            if not case_sensitive:
                res = dict_key_to_upper(res)
            return res
        return {}


def yaml_config_setting_source(base_settings: BaseSettings) -> Dict[str, Any]:
    """
    yaml config.
    :param base_settings:
    :return:
    """
    encoding = base_settings.__config__.env_file_encoding
    case_sensitive = base_settings.__config__.case_sensitive
    with Path('ble_assistant.yml') as f:
        if f.exists():
            res = yaml.full_load(f.read_text(encoding))
            if not case_sensitive:
                res = dict_key_to_upper(res)
            return res
        return {}


class Settings(BaseSettings):
    """
    Base settings.
    """
    DEVICE: str = 'ble'
    PARSER: bool = True
    SCAN_PRINT: bool = False
    COSTTIME: bool = False
    # serial
    BAUDRATE: int = 460800
    TIMEOUT: int = 2
    # protocol
    BYTE_ORDER = 'little'
    HEADER_DOWNLINK: bytes = b'\xaa'
    HEADER_UPLINK: list = [b'\xbb', b'\xdd']
    HEADER_LOG: bytes = b'\xff'
    HEADER_BALI_LOG: bytes = b'\xc7'
    BALI_LOG_DESCRIPT: str = os.path.join(
        os.getcwd(),
        './ble_uplink_desc.xml',
    )

    @validator('HEADER_DOWNLINK',
               'HEADER_LOG',
               pre=True)
    def get_header(
            cls,
            v: Union[bytes, int],
    ) -> bytes:
        if isinstance(v, int):
            return v.to_bytes(
                1,
                'little',
            )
        return v

    HEADER_SIZE: int = len(HEADER_DOWNLINK)
    MODEL_SIZE: int = 1
    OPCODE_SIZE: int = 1
    PROTOCOL_SIZE: int = HEADER_SIZE + MODEL_SIZE + OPCODE_SIZE
    DATA_LEN_INDEX: int = PROTOCOL_SIZE
    DATA_LEN_SIZE: int = 2
    PAYLOAD_INDEX: int = DATA_LEN_INDEX + DATA_LEN_SIZE
    CHECKSUM_SIZE: int = 1
    FRAME_MIN_SIZE: int = PROTOCOL_SIZE + DATA_LEN_SIZE + CHECKSUM_SIZE

    # report
    REPORT_PATH: str = os.path.join(os.getcwd(), 'reports')
    # log
    LOG_PATH: str = os.path.join(os.getcwd(), 'logs')
    LOG_NAME: str = 'ble_test'
    LOG_LEVEL: int = logging.DEBUG
    LOG_STDOUT: bool = True
    LOG_FORMATTER: str = '[%(asctime)s][%(levelname)s][%(funcName)s]%(message)s'
    DONGLE_LOG_NAME: str = 'ble_dongle'
    DONGLE_LOG_ENABLE: bool = True
    DONGLE_LOG_FORMATTER: str = '[%(asctime)s]%(message)s'
    DONGLE_LOG_BACKUP_COUNT: int = 100
    SERIAL_LOG_NAME: str = 'serial'
    SERIAL_LOG_ENABLE: bool = True
    SERIAL_LOG_FORMATTER: str = '[%(asctime)s]%(message)s'
    SERIAL_LOG_BACKUP_COUNT: int = 100

    # url or ip
    TEST_MANAGE_URL: HttpUrl = 'http://localhost:8080'
    GLOG_URL = 'ws://localhost:5688'

    # UI
    BACKGROUND_COLOR: str = '#eceade'

    class Config:
        case_sensitive = False
        env_file_encoding = 'utf-8'

        @classmethod
        def customise_sources(
                cls,
                init_settings,
                env_settings,
                file_secret_settings,
        ):
            return (
                init_settings,
                env_settings,
                yaml_config_setting_source,
                json_config_setting_source,
                file_secret_settings,
            )


settings = Settings()
