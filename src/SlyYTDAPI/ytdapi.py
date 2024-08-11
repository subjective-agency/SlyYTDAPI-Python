import re
from enum import Enum
from datetime import datetime
from typing import TypeVar, Any
from warnings import warn
from SlyAPI import *

SCOPES_ROOT = 'https://www.googleapis.com/auth/youtube'

class Scope:
    READONLY     = F"{SCOPES_ROOT}.readonly"
    MEMBERS      = F"{SCOPES_ROOT}.channel-memberships.creator"

class Part(Enum):
    ID                      = 'id'                          # quota cost: 0
    DETAILS                 = 'contentDetails'              # quota cost: 2
    SNIPPET                 = 'snippet'                     # quota cost: 2
    STATUS                  = 'status'                      # quota cost: 2
    STATISTICS              = 'statistics'                  # quota cost: 2
    REPLIES                 = 'replies'                     # quota cost: 2
    LIVESTREAM_DETAILS      = 'liveStreamingDetails'        # quota cost: x
    TOPIC_DETAILS           = 'topicDetails'                # quota cost: x
    RECORDING_DETAILS       = 'topicDetails'                # quota cost: x
    LOCALIZATIONS           = 'topicDetails'                # quota cost: x
    # ...

class PrivacyStatus(Enum):
    PRIVATE      = 'private'
    UNLISTED     = 'unlisted'
    PUBLIC       = 'public'

class SafeSearch(Enum):
    SAFE         = 'strict'
    MODERATE     = 'moderate'
    UNSAFE       = 'none'

class Order(Enum):
    DATE         = 'date'
    LIKES        = 'rating'
    RELEVANCE    = 'relevance'
    ALPHABETICAL = 'title'
    VIEWS        = 'viewCount'

class CommentOrder(Enum):
    RELEVANCE    = 'relevance'
    TIME         = 'time'

ISO8601_PERIOD = re.compile(r'P(\d+)?T(?:(\d{1,2})H)?(?:(\d{1,2})M)?(\d{1,2})S')

def yt_date(date: str) -> datetime:
    try:
        return datetime.strptime(date, '%Y-%m-%dT%H:%M:%S.%fZ')
    except ValueError:
        return datetime.strptime(date, '%Y-%m-%dT%H:%M:%SZ')

W = TypeVar('W')
T = TypeVar('T')

def get_dict_path(d: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        if key not in d:
            return None
        d = d[key]
    return d
    
class Comment:
    id: str
    # part: snippet
    author_display_name: str
    author_channel_id: str
    body: str
    created_at: datetime
    # part: replies
    replies: list['Comment']|None

    @property
    def author_name(self):
        warn("author_name is deprecated, please use author_display_name")
        return self.author_display_name

    def __init__(self, source: dict[str, Any]):
        # case of top-level comment
        if tlc := source.get('snippet', {}).get('topLevelComment'):
            replies: list[Any] = source.get('replies', {}).get('comments', [])
            self.replies = [Comment(r) for r in replies]
            source = tlc
            
        self.id = source['id']
        if snippet := source.get('snippet'):
            self.author_display_name = snippet['authorDisplayName']
            self.author_channel_id = snippet['authorChannelId']['value']
            self.body = snippet['textDisplay']
            self.created_at = yt_date(snippet['publishedAt'])
        


class Video:
    _youtube: 'YouTubeData'
    id: str

    # part: snippet
    title: str
    description: str
    published_at: datetime
    channel_id: str
    channel_name: str
    tags: list[str]
    is_livestream: bool
    default_audio_language: str | None
    thumbnails: list[str] | None = None
    localized_title: str | None = None
    localized_description: str | None = None

    # part: contentDetails
    duration: int | None = None
    is_licensed: bool | None = None
    blocked_in: list[str] | None = None
    allowed_in: list[str] | None = None
    dimension: str | None = None
    definition: str | None = None
    caption: str | None = None
    projection: str | None = None

    # part: status
    privacy: PrivacyStatus
    upload_status: str | None = None
    failure_reason: str | None = None
    rejection_reason: str | None = None
    license: str | None = None
    is_embeddable: bool | None = None
    has_viewable_stats: bool | None = None
    is_made_for_kids: bool | None = None
    self_declared_made_for_kids: bool | None = None

    # part: statistics
    view_count: int | None = None
    like_count: int | None = None
    favourite_count: int | None = None

    # dislike_count: int ## rest in peace
    comment_count: int | None = None

    # part: liveStreamingDetails
    livestream_details: dict[str, Any] | None
    
    # part: topicDetails
    topic_categories: list[str] | None
    
    # part: localizations
    localizations: dict[str, Any] | None
    
    # part: recordingDetails
    recording_date: datetime | None
    
    def to_dict(self) -> dict[str, Any]:
        """
        Returns a dictionary representation of the Video object.
        """
        video_dict = {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'published_at': self.published_at.isoformat(),
            'channel_id': self.channel_id,
            'channel_name': self.channel_name,
            'tags': self.tags,
            'is_livestream': self.is_livestream,
            'default_audio_language': self.default_audio_language,
            'thumbnails': self.thumbnails,
            'localized_title': self.localized_title,
            'localized_description': self.localized_description,
            'duration': self.duration,
            'is_licensed': self.is_licensed,
            'blocked_in': self.blocked_in,
            'allowed_in': self.allowed_in,
            'dimension': self.dimension,
            'definition': self.definition,
            'caption': self.caption,
            'projection': self.projection,
            'privacy': self.privacy,
            'upload_status': self.upload_status,
            'failure_reason': self.failure_reason,
            'rejection_reason': self.rejection_reason,
            'license': self.license,
            'is_embeddable': self.is_embeddable,
            'has_viewable_stats': self.has_viewable_stats,
            'is_made_for_kids': self.is_made_for_kids,
            'self_declared_made_for_kids': self.self_declared_made_for_kids,
            'view_count': self.view_count,
            'like_count': self.like_count,
            'favourite_count': self.favourite_count,
            'comment_count': self.comment_count,
            'livestream_details': self.livestream_details,
            'topic_categories': self.topic_categories,
            'localizations': self.localizations,
            'recording_date': self.recording_date.isoformat() if self.recording_date else None
        }
        return video_dict

    def __init__(self, source: dict[str, Any], yt: 'YouTubeData'):
        self._youtube = yt
        match source['id']:
            case str():
                self.id = source['id']
            case dict(): # case for video search result object
                self.id = source['id']['videoId']
            case _:
                raise ValueError("Video expects source id to be a string or dict")
        
        if snippet := source.get('snippet'):
            self.title = snippet['title']
            self.description = snippet['description']
            self.published_at = yt_date(snippet['publishedAt'])
            self.channel_id = snippet['channelId']
            self.channel_name = snippet['channelTitle']
            self.tags = snippet.get('tags', [])
            self.is_livestream = snippet.get('liveBroadcastContent') == 'live'
            self.default_audio_language = snippet.get('defaultAudioLanguage')

            self.thumbnails = [x.get("url") for x in snippet.get("thumbnails", {}).values()]
            self.localized_title = snippet.get("localized", {}).get("title")
            self.localized_description = snippet.get("localized", {}).get("description")    

        if contentDetails := source.get('contentDetails'):
            m = ISO8601_PERIOD.match(contentDetails['duration'])
            if m:
                days, hours, minutes, seconds = (int(g) if g else 0 for g in m.groups())
                self.duration = days * 24 * 60 * 60 + hours * 60 * 60 + minutes * 60 + seconds
            else:
                raise ValueError(F"Unknown duration format: {contentDetails['duration']}")
            self.is_licensed=contentDetails.get('licensedContent')
            self.blocked_in=contentDetails.get("regionRestriction", {}).get("blocked")
            self.allowed_in=contentDetails.get("regionRestriction", {}).get("allowed")
            
            self.dimension=contentDetails.get("dimension")
            self.definition=contentDetails.get("definition")
            self.caption=contentDetails.get("caption")
            self.projection=contentDetails.get("projection")
            # TODO: contentRating

        if status := source.get('status'):
            self.privacy = status.get('privacyStatus')
            
            self.uploadStatus = status.get('uploadStatus')
            self.failureReason = status.get('failureReason')
            self.rejectionReason = status.get('rejectionReason')
            self.license = status.get('license')
            self.is_embeddable = status.get('embeddable')
            self.has_viewable_stats = status.get('publicStatsViewable')
            self.is_made_for_kids = status.get('madeForKids')
            self.self_declared_made_for_kids = status.get('selfDeclaredMadeForKids')

        if statistics := source.get('statistics'):
            self.view_count = int(statistics['viewCount'])
            self.like_count = int(statistics['likeCount'])
            self.comment_count = int(statistics['commentCount'])
            self.favourite_count = int(statistics['favouriteCount'])

        if liveStreamingDetails := source.get('liveStreamingDetails'):
            self.livestream_details=liveStreamingDetails

        if topicDetails := source.get('topicDetails'):
            self.topic_categories=topicDetails.get('topicCategories')

        if recordingDetails := source.get('recordingDetails'):
            self.recording_date=recordingDetails.get('recordingDate')

        if fileDetails := source.get('fileDetails'):
            self.file_name = fileDetails.get('fileName')
            self.file_size = fileDetails.get('fileSize')
            self.file_type = fileDetails.get('fileType')
            self.container = fileDetails.get('container')
            self.durationMs = fileDetails.get('durationMs')
            self.bitrateBps = fileDetails.get('bitrateBps')
            self.creationTime = fileDetails.get('creationTime')
            # TODO: videoStreams
            # TODO: audioStreams

        if suggestions := source.get('suggestions'):
            self.processing_errors = suggestions.get('processingErrors')
            self.processing_warnings = suggestions.get('processingWarnings')
            self.processing_hints = suggestions.get('processingHints')
            self.tag_suggestions = suggestions.get('tagSuggestions')
            self.editor_suggestions = suggestions.get('editorSuggestions')

        if processingDetails := source.get('processingDetails'):
            self.processing_status = processingDetails.get('processingStatus')
            self.processing_progress = processingDetails.get('processingProgress')
            
        if localizations := source.get('localizations'):
            self.localizations=localizations

    def link(self, short: bool = False) -> str:
        if not short:
            return F"https://www.youtube.com/watch?v={self.id}"
        else:
            return F"https://youtu.be/{self.id}"

    def comments(self, limit: int | None = 100) -> AsyncTrans[Comment]:
        return self._youtube.comments(self.id, limit=limit)

    async def channel(self) -> 'Channel':
        return await self._youtube.channel(self.channel_id)

class Playlist:
    _youtube: 'YouTubeData'
    id: str

    def __init__(self, id: str, yt: 'YouTubeData'):
        self._youtube = yt
        self.id = id

    def link(self) -> str:
        return F"https://www.youtube.com/playlist?list={self.id}"

class Channel:
    _youtube: 'YouTubeData'
    id: str

    # part: snippet
    display_name: str
    description: str
    created_at: datetime
    at_username: str
    profile_image_url: str|None = None

    # part: contentDetails
    uploads_playlist: Playlist

    # part: statistics
    view_count: int
    subscriber_count: int
    video_count: int

    @property
    def custom_url(self):
        warn("custom_url is deprecated, please use at_username")
        return self.at_username

    
    @property
    def name(self):
        warn("name is deprecated, please use display_name")
        return self.display_name

    def __init__(self, source: dict[str, Any], yt: 'YouTubeData'):
        self._youtube = yt

        self.id = source['id']
        if snippet := source.get('snippet'):
            self.display_name = snippet['title']
            self.description = snippet['description']
            self.created_at = yt_date(snippet['publishedAt'])
            self.profile_image_url = snippet.get('thumbnails', {}).get('default', {}).get('url')
            self.at_username = snippet.get('customUrl')

        if details := source.get('contentDetails'):
            self.uploads_playlist = Playlist(details['relatedPlaylists']['uploads'], yt)

        if stats := source.get('statistics'):
            self.view_count = int(stats['viewCount'])
            self.subscriber_count = int(stats['subscriberCount'])
            self.video_count = int(stats['videoCount'])

    def link(self) -> str:
        if self.at_username:
            return F"https://www.youtube.com/c/{self.at_username}"
        else:
            return F"https://www.youtube.com/channels/{self.id}"

    async def update(self):
        new = await self._youtube.channel(self.id)
        self.__dict__.update(new.__dict__)

    def videos(self, limit: int|None=None, mine: bool|None=None) -> AsyncTrans[Video]:
        return self._youtube.search_videos(channel_id=self.id, limit=limit, mine=mine)

class YouTubeData(WebAPI):
    base_url = 'https://www.googleapis.com/youtube/v3'

    def __init__(self, app_or_api_key: str|OAuth2|UrlApiKey) -> None:
        match app_or_api_key:
            case str():
                auth = UrlApiKey('key', app_or_api_key)
            case _:
                auth = app_or_api_key
        super().__init__(auth)

    async def my_channel(self, parts: Part=Part.SNIPPET) -> Channel:
        return (await self._channels_list(mine=True, parts=parts, limit=1))[0]

    async def channels(self, channel_ids: list[str], parts: Part) -> list[Channel]:
        return await self._channels_list(channel_ids=channel_ids, parts=parts)

    async def channel(self, channel_id: str, parts: Part=Part.SNIPPET) -> Channel:
        return (await self._channels_list(channel_ids=[channel_id], parts=parts))[0]

    def _channels_list(self,
        channel_ids: list[str]|None=None,
        mine: bool=False,
        parts: Part|set[Part]=Part.SNIPPET,
        limit: int|None=None) -> AsyncTrans[Channel]:
        if mine==bool(channel_ids):
            raise ValueError("Must specify exactly one of channel id or mine in channel list query")
        maxResults = min(50, limit) if limit else None # per-page limit
        params = { 'part': parts, 'maxResults': maxResults }
        if channel_ids:
            channel_ids = list(set(channel_ids or [])) # deduplicate IDs
            channels_chunks50 = [
                channel_ids[i: i + 50] for i in range(0, len(channel_ids), 50)
            ]
            async def page_chunks():
                for ids in channels_chunks50:
                    p = params | { 'id': ','.join(ids) }
                    async for c in self.paginated('/channels', p, limit):
                        yield c
            return AsyncLazy(page_chunks()).map(lambda r: Channel(r, self))
        else: # mine
            return self.paginated(
                '/channels', params | { 'mine': True }, limit
                ).map(lambda r: Channel(r, self))

    def videos(self,
        video_ids: list[str],
        parts: Part|set[Part]={Part.ID,Part.SNIPPET}) -> AsyncTrans[Video]:
        params = {
            'part': parts,
            'id': ','.join(video_ids),
        }
        return self.paginated(
            '/videos', params, None
            ).map(lambda r: Video(r, self))

    async def video(self, id: str, parts: Part|set[Part]={Part.ID,Part.SNIPPET}) -> Video:
        return (await self.videos([id], parts))[0]

    def get_playlist_videos(self,
        playlist_id: str, 
        parts: Part|set[Part]=Part.SNIPPET,
        limit: int|None=None) -> AsyncTrans[Video]:
        params = {
            'part': parts,
            'playlistId': playlist_id,
            'maxResults': min(50, limit) if limit else None,
        }
        return self.paginated(
            '/playlistItems', params, limit
            ).map(lambda r: Video(r, self))

    def search_videos(self,
        query: str|None=None,
        channel_id: str|None=None,
        after: datetime|None=None,
        before: datetime|None=None,
        mine: bool|None=None,
        order: Order=Order.RELEVANCE,
        safeSearch: SafeSearch=SafeSearch.MODERATE,
        parts: Part|set[Part]=Part.SNIPPET,
        limit: int|None=50) -> AsyncTrans[Video]:
        params = {
            'part': parts,
            'safeSearch': safeSearch,
            'order': order,
            'type': 'video',
            'q': query,
            'channelId': channel_id,
            'forMine': mine,
            'publishedAfter': after.isoformat("T") + "Z" if after else None,
            'publishedBefore': before.isoformat("T") + "Z" if before else None,
            'maxResults': min(50, limit) if limit else None,
        }

        return self.paginated(
            '/search', params, limit
            ).map(lambda r: Video(r, self))

    def comments(self,
        video_id: str,
        query: str|None=None,
        parts: Part|set[Part]={Part.SNIPPET,Part.REPLIES},
        order: CommentOrder=CommentOrder.TIME,
        limit: int|None=None) -> AsyncTrans[Comment]:
        params = {
            'part': parts,
            'commentOrder': order,
            'searchTerms': query,
            'videoId': video_id,
            'maxResults': min(100, limit) if limit else None,
        }
        return self.paginated(
            '/commentThreads', params, limit
            ) .map(Comment)
    