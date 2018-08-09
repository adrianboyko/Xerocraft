
# Standard

# Third Party
from rest_framework import serializers

# Local
import kmkr.models as models


class ShowSerializer(serializers.ModelSerializer):

    class Meta:
        model = models.Show
        fields = (
            'id',
            'title',
            'duration',
            'description',
            'active'
        )


class ManualPlayListEntrySerializer(serializers.ModelSerializer):

    live_show_instance = serializers.HyperlinkedRelatedField(
        view_name='kmkr:showinstance-detail',
        queryset = models.ShowInstance.objects.all(),
    )

    class Meta:
        model = models.ManualPlayListEntry
        fields = (
            'id',
            'live_show_instance',
            'sequence',
            'artist',
            'title',
            'duration'
        )


class ShowInstanceSerializer(serializers.ModelSerializer):

    show = serializers.HyperlinkedRelatedField(
        view_name='kmkr:show-detail',
        queryset = models.Show.objects.all()
    )
    playlist_embed = ManualPlayListEntrySerializer(many=True, read_only=True, source='manualplaylistentry_set')

    class Meta:
        model = models.ShowInstance
        fields = (
            'id',
            'show',
            'date',
            'host_checked_in',
            'repeat_of',
            'playlist_embed'
        )


class TrackSerializer(serializers.ModelSerializer):

    class Meta:
        model = models.Track
        fields = (
            'id',
            'title',
            'artist',
            'radiodj_id',
            'track_type',
            'duration'
        )


class PlayLogEntrySerializer(serializers.ModelSerializer):

    track_embed = TrackSerializer(many=False, read_only=True, source='track')

    class Meta:
        model = models.PlayLogEntry
        fields = (
            'id',
            'track_embed',
            'start',
        )
