"""Test script for video processing pipeline."""
from app.modules.perception.video_processor import process_video_camera


def test_video_processor():
    """Test the video processor with CityFlow c020 video."""
    result = process_video_camera(
        video_path='D:/coding/TRACE/data/footage/c020/vdo.avi',
        camera_id='c020',
        confidence=0.25,
    )

    print('=== Video Processor Test ===')
    print('Camera:', result.get('camera_id'))
    print('Status:', result.get('camera_status'))
    print('Observations count:', len(result.get('observations', [])))

    if result.get('observations'):
        obs = result['observations'][0]
        print('First obs keys:', list(obs.keys()))
        print('First obs plate_text:', obs.get('fused_plate_text'))
        print('First obs confidence:', obs.get('fused_confidence'))
        print('First obs camera_id:', obs.get('camera_id'))

    print('=== Test Complete ===')


if __name__ == '__main__':
    test_video_processor()