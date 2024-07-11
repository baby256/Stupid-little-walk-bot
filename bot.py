import os
import sys
from enum import IntEnum

import numpy
import requests.exceptions
import telebot
from loguru import logger
from telebot.types import Message

bot = telebot.TeleBot(os.environ["BOT_TOKEN"])

user_data = {}


class DialogState(IntEnum):
    initial = 0
    awaiting_radius = 1


def get_dialog_state(message: Message) -> DialogState:
    if message.from_user.id not in user_data:
        return DialogState.initial
    return user_data[message.from_user.id]


@bot.message_handler(content_types=["text", "location"])
def handle_message(message: Message):
    logger.info(
        f"got message from user {message.from_user.id} {message.from_user.username}"
    )
    if message.text == "/start":
        bot.send_message(
            message.from_user.id,
            "Привет! Пришли мне свою геолокацию и я придумаю куда тебе прогуляться.",
        )

    if get_dialog_state(message) == DialogState.initial:
        handle_initial_state(message)
    if get_dialog_state(message) == DialogState.awaiting_radius:
        handle_awaiting_radius_state(message)


def handle_awaiting_radius_state(message: Message):
    if int(message.text) >= 6371000:
        bot.send_message(
            message.from_user.id, "Это слишком большой радиус, попробуй еще раз."
        )
    elif int(message.text) == 0:
        bot.send_message(message.from_user.id, "Радиус должен быть больше нуля.")
    else:
        lat, lon = make_random_point(
            message.location.latitude, message.location.longitude, int(message.text)
        )
        bot.send_location(message.from_user.id, lat, lon)
        user_data[message.from_user.id] = DialogState.initial


def handle_initial_state(message: Message):
    if message.location:
        bot.send_message(message.from_user.id, "Укажи желаемый радиус (в метрах)")
        user_data[message.from_user.id] = DialogState.awaiting_radius
    else:
        bot.send_message(
            message.from_user.id,
            "Извини, я бы и рад с тобой поболтать, но у меня много дел. Давай лучше помогу тебе с планом прогулки."
            " Пришли мне геолокацию!",
        )


EARTH_RADIUS = 6371000


def make_random_point(lat, long, radius) -> tuple[float, float]:
    angle = numpy.longdouble(2 * numpy.pi * numpy.random.random_sample())
    radius = numpy.longdouble(radius) * numpy.random.random_sample()

    latitudinal_diff_rad = radius * numpy.sin(angle) / numpy.longdouble(EARTH_RADIUS)
    longitudinal_diff_rad = radius * numpy.cos(angle) / numpy.longdouble(EARTH_RADIUS)

    latitudinal_diff = latitudinal_diff_rad * 180 / numpy.pi
    longitudinal_diff = longitudinal_diff_rad * 180 / numpy.pi

    latitude = numpy.longdouble(lat) + latitudinal_diff
    longitude = numpy.longdouble(long) + longitudinal_diff
    return latitude, longitude


if __name__ == "__main__":
    logger.add(sys.stderr, format="{time} {level} {message}", level="INFO")
    while True:
        try:
            bot.polling(none_stop=True, interval=0)
        except requests.exceptions.ReadTimeout as e:
            logger.exception("read timeout. restarting")
