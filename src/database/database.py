from typing import Iterable
import sqlite3 as sql
import datetime, os

from .event import Event
from src.utils.logs import database_logger

def to_epoch(date: datetime.datetime) -> int:
    return int(date.timestamp())

def from_epoch(epoch: int) -> datetime.datetime:
    return datetime.datetime.fromtimestamp(int(epoch))

sql.register_adapter(datetime.datetime, to_epoch)
sql.register_converter("DATETIME", from_epoch)


def file_entry_datetime(entry: os.DirEntry) -> datetime.datetime:
    try:
        name = entry.name
        head, _ = os.path.splitext(name)
        sep_index = - head[::-1].index('_') - 1
        time = head[sep_index + 1:]
        return datetime.datetime.strptime(time, '%Y-%m-%dT%H%M')
    
    except:
        return datetime.datetime.fromtimestamp(0)

class DatabaseAccessor:
    '''Class that manages the database.'''

    def __init__(self, dbpath: str, max_backups: int = 3):
        self.dbpath = dbpath
        self.max_backups = max_backups

        with sql.connect(dbpath) as db:
            cursor = db.cursor()
            cursor.execute('SELECT name FROM sqlite_master WHERE type="table" AND name="events"')
            if cursor.fetchone() is None:
                database_logger.info('create events table')
                self.create_events_table()


    def create_events_table(self):
        '''Initializes the events table in the database.'''

        with sql.connect(self.dbpath) as db:
            cursor = db.cursor()
            cursor.execute("DROP TABLE IF EXISTS events")
            # Ideally we need a sorted table, sqlite supposedly implements this
            # with clustered indexes, however my sorting id is not unique.
            # I also have to enforce that each entry is unique in total
            # For now, I've set the primary key as every column putting 
            # the important ones first for the sorting. However, this might not 
            # be the best way to do it.
            cursor.execute(
                'CREATE TABLE events ('
                    'category TEXT, '
                    'description TEXT, '
                    'start DATETIME, '
                    'end DATETIME, '
                    'location TEXT, '
                    'guild_id INTEGER, '
                    'PRIMARY KEY (guild_id, end, start, category, description, location)'
                ') WITHOUT ROWID'
            )


    def get_calendar(self, guild_id: int) -> Iterable[Event]:
        '''Returns all events in the database.'''

        with sql.connect(self.dbpath, detect_types=sql.PARSE_DECLTYPES) as db:
            cursor = db.cursor()
            database_logger.info('retrieve events table')
            cursor.execute(
                'SELECT * FROM events WHERE guild_id = ?',
                (guild_id,)
            )
            raw = cursor.fetchall()
            db.commit()
            
        return (Event(*entry) for entry in raw)


    def put_event(self, event: Event) -> bool:
        '''Adds an event to the database.'''

        try:
            with sql.connect(self.dbpath) as db:
                cursor = db.cursor()
                database_logger.info(f'insert event {event.to_tuple()}')
                cursor.execute(
                    'INSERT INTO events VALUES (?, ?, ?, ?, ?, ?)',
                    event.to_tuple()
                )
                db.commit()
            return True
        
        except:
            return False
        

    def remove_event(self, event: Event) -> bool:
        '''Deletes an event from the database.'''

        try:
            with sql.connect(self.dbpath) as db:
                cursor = db.cursor()
                database_logger.info(f'delete event {event.to_tuple()}')
                cursor.execute(
                    'DELETE FROM events WHERE '
                        'category = ? AND '
                        'description = ? AND '
                        'start = ? AND '
                        'end = ? AND '
                        'location = ? AND '
                        'guild_id = ?'
                    ,
                    event.to_tuple()
                )
                db.commit()
            return True
        
        except:
            return False
       
        
    def edit_event(self, old_event: Event, new_event: Event) -> bool:
        '''Edits an event in the database.'''

        try:
            with sql.connect(self.dbpath) as db:
                cursor = db.cursor()

                old_event_tuple = old_event.to_tuple()

                # Retrieve changes
                changes = tuple(
                    new if old != new else None
                    for old, new
                    in zip(old_event_tuple, new_event.to_tuple())
                )

                # Create the set clause template
                set_clause = ', '.join(
                    change for change in (
                        'category = ?' if changes[0] else '',
                        'description = ?' if changes[1] else '',
                        'start = ?' if changes[2] else '',
                        'end = ?' if changes[3] else '',
                        'location = ?' if changes[4] else '',
                        'guild_id = ?' if changes[5] else '',
                    ) if change
                )
                if not set_clause: raise ValueError('No changes were made.')
                # Remove None values
                set_values = (change for change in changes if change)

                database_logger.info(f'modify event {old_event_tuple} -> {changes}')
                cursor.execute(
                    'UPDATE events SET '
                        + set_clause + ' '
                    'WHERE '
                        'category = ? AND '
                        'description = ? AND '
                        'start = ? AND '
                        'end = ? AND '
                        'location = ? AND '
                        'guild_id = ?'
                    ,
                    (*set_values, *old_event_tuple)
                )
                db.commit()
            return True
        
        except:
            return False
    
    def update(self) -> None:
        '''Removes all events that have already ended.'''

        now = int(datetime.datetime.now().timestamp())
        with sql.connect(self.dbpath) as db:
            cursor = db.cursor()
            database_logger.info('removing old events')
            cursor.execute('DELETE FROM events WHERE end < ?', (now,))
            db.commit()


    def sync(self, scheduled_events: Iterable[Event], guild_id: int) -> None:
        '''Syncs the database with the scheduled events.'''

        db_events = set(self.get_calendar(guild_id))
        scheduled_events = set(scheduled_events)

        for event in scheduled_events:
            if event not in db_events:
                self.put_event(event)

        for event in db_events:
            if event not in scheduled_events:
                self.remove_event(event)

    # The backup is for every server, not many should have accesss to this
    def backup(self):
        '''Creates a backup of the database.'''

        if self.max_backups < 1: return

        time = '_' + datetime.datetime.now().strftime('%Y-%m-%dT%H%M')
        head, tail = os.path.split(self.dbpath)
        name, ext = os.path.splitext(tail)
        backups_path = os.path.join(head, 'backups')


        files = [*os.scandir(backups_path)]
        if len(files) >= self.max_backups:
            files.sort(key=file_entry_datetime) 
            for entry in files[:len(files) - self.max_backups + 1]:
                os.remove(entry.path)

        os.path.isdir(backups_path) or os.mkdir(backups_path)
        with sql.connect(self.dbpath) as db:
            with sql.connect(os.path.join(backups_path, name + time + ext)) as backup:
                db.backup(backup)
        
        database_logger.info('backup created')
