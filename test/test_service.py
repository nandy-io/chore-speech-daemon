import unittest
import unittest.mock

import os
import json

import service


class MockRedis(object):

    def __init__(self, host, port):

        self.host = host
        self.port = port
        self.channel = None
        self.messages = []

    def pubsub(self):

        return self

    def subscribe(self, channel):

        self.channel = channel

    def get_message(self):

        return self.messages.pop(0)


class TestService(unittest.TestCase):

    @unittest.mock.patch.dict(os.environ, {
        "REDIS_HOST": "most.com",
        "REDIS_PORT": "667",
        "REDIS_CHANNEL": "stuff",
        "SPEECH_API": "http://boast.com",
        "SLEEP": "0.7"
    })
    @unittest.mock.patch("redis.StrictRedis", MockRedis)
    def setUp(self):

        self.daemon = service.Daemon()

    @unittest.mock.patch.dict(os.environ, {
        "REDIS_HOST": "most.com",
        "REDIS_PORT": "667",
        "REDIS_CHANNEL": "stuff",
        "SPEECH_API": "http://boast.com",
        "SLEEP": "0.7"
    })
    @unittest.mock.patch("redis.StrictRedis", MockRedis)
    def test___init___(self):

        daemon = service.Daemon()

        self.assertEqual(daemon.redis.host, "most.com")
        self.assertEqual(daemon.redis.port, 667)
        self.assertEqual(daemon.channel, "stuff")
        self.assertEqual(daemon.speech, "http://boast.com/speak")
        self.assertEqual(daemon.sleep, 0.7)

    def test_subscribe(self):

        self.daemon.subscribe()

        self.assertEqual(self.daemon.redis, self.daemon.pubsub)
        self.assertEqual(self.daemon.redis.channel, "stuff")

    @unittest.mock.patch("service.time.time", unittest.mock.MagicMock(return_value=7))
    @unittest.mock.patch("requests.post")
    def test_speak(self, mock_post):

        self.daemon.speak("hey")

        mock_post.assert_called_with("http://boast.com/speak", json={
            "timestamp": 7,
            "text": "hey"
        })

        mock_post.assert_has_calls([
            unittest.mock.call("http://boast.com/speak", json={
                "timestamp": 7,
                "text": "hey"
            }),
            unittest.mock.call().raise_for_status()
        ])

        mock_post.reset_mock()

        self.daemon.speak(
            "hey",
            {"node": "bump", "language": "cursing"},
            "dude"
        )

        mock_post.assert_has_calls([
            unittest.mock.call("http://boast.com/speak", json={
                "timestamp": 7,
                "text": "dude, hey",
                "node": "bump",
                "language": "cursing"
            }),
            unittest.mock.call().raise_for_status()
        ])

    @unittest.mock.patch("service.time.time", unittest.mock.MagicMock(return_value=7))
    @unittest.mock.patch("requests.post")
    def test_process(self, mock_post):

        self.daemon.subscribe()

        self.daemon.redis.messages = [
            None,
            {"data": 1},
            {
                "data": json.dumps({
                    "kind": "routine",
                    "action": "create",
                    "routine": {
                        "data": {
                            "text": "hey",
                            "speech": True
                        }
                    },
                    "person": {
                        "name": "dude"
                    }
                })
            },
            {
                "data": json.dumps({
                    "kind": "task",
                    "action": "create",
                    "routine": {
                        "data": {
                            "speech": {
                                "node": "bump",
                                "language": "cursing"
                            }
                        }
                    },
                    "task": {
                        "text": "you"
                    },
                    "person": {
                        "name": "dude"
                    }
                })
            },
            {
                "data": json.dumps({
                    "kind": "todo",
                    "speech": {
                        "node": "bump",
                        "language": "cursing"
                    },
                    "todos": [
                        {
                            "data": {
                                "text": "guys"
                            }
                        }
                    ],
                    "person": {
                        "name": "dude"
                    }
                })
            }
        ]

        self.daemon.process()
        self.daemon.process()

        self.daemon.process()
        mock_post.assert_has_calls([
            unittest.mock.call("http://boast.com/speak", json={
                "timestamp": 7,
                "text": "dude, time to hey."
            }),
            unittest.mock.call().raise_for_status()
        ])

        mock_post.reset_mock()
        self.daemon.process()
        mock_post.assert_has_calls([
            unittest.mock.call("http://boast.com/speak", json={
                "timestamp": 7,
                "text": "dude, time to you.",
                "node": "bump",
                "language": "cursing"
            }),
            unittest.mock.call().raise_for_status()
        ])

        mock_post.reset_mock()
        self.daemon.process()
        mock_post.assert_has_calls([
            unittest.mock.call("http://boast.com/speak", json={
                "timestamp": 7,
                "text": "dude, these are your current todos:",
                "node": "bump",
                "language": "cursing"
            }),
            unittest.mock.call().raise_for_status(),
            unittest.mock.call("http://boast.com/speak", json={
                "timestamp": 7,
                "text": "guys",
                "node": "bump",
                "language": "cursing"
            }),
            unittest.mock.call().raise_for_status()
        ])

    @unittest.mock.patch("service.time.time", unittest.mock.MagicMock(return_value=7))
    @unittest.mock.patch("requests.post")
    @unittest.mock.patch("service.time.sleep")
    @unittest.mock.patch("traceback.format_exc")
    @unittest.mock.patch('builtins.print')
    def test_run(self, mock_print, mock_traceback, mock_sleep, mock_post):

        self.daemon.redis.messages = [
            {
                "data": json.dumps({
                    "kind": "routine",
                    "action": "create",
                    "routine": {
                        "data": {
                            "text": "hey",
                            "speech": True
                        }
                    },
                    "person": {
                        "name": "dude"
                    }
                })
            },
            None
        ]

        mock_sleep.side_effect = [Exception("whoops"), Exception("adaisy")]
        mock_traceback.side_effect = ["spirograph", Exception("doh")]

        self.assertRaisesRegex(Exception, "doh", self.daemon.run)

        self.assertEqual(self.daemon.redis, self.daemon.pubsub)
        self.assertEqual(self.daemon.redis.channel, "stuff")

        mock_post.assert_has_calls([
            unittest.mock.call("http://boast.com/speak", json={
                "timestamp": 7,
                "text": "dude, time to hey."
            }),
            unittest.mock.call().raise_for_status()
        ])

        mock_sleep.assert_called_with(0.7)

        mock_print.assert_has_calls([
            unittest.mock.call("whoops"),
            unittest.mock.call("spirograph"),
            unittest.mock.call("adaisy")
        ])