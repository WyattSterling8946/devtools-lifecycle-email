from src.email_lifecycle import LifecycleEvent, should_notify


def test_release_with_detail_is_notified_but_empty_build_is_not():
    assert should_notify(LifecycleEvent.RELEASE, "v2.4.0 is live") is True
    assert should_notify(LifecycleEvent.BUILD, "   ") is False
