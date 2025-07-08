#!/usr/bin/env python3
"""
Comprehensive RunSignUp Integration Testing Script (SQLite Version)

Tests:
1. Full syncs of future events for all credential sets
2. Incremental syncs (only modified records since last sync)  
3. Bib assignment triggers (when bibs are assigned in RunSignUp)
"""

import sys
import os
import sqlite3
import json
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional

# Add the current directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from providers.runsignup_adapter import RunSignUpAdapter

# Configure detailed logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('test_runsignup_comprehensive.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

class RunSignUpComprehensiveTest:
    """Comprehensive RunSignUp integration testing using SQLite"""
    
    def __init__(self):
        self.db_path = "../../race_results.db"
        
        self.test_results = {
            'full_sync_test': {},
            'incremental_sync_test': {},
            'bib_assignment_test': {},
            'summary': {}
        }
        
    def get_connection(self):
        """Get SQLite database connection"""
        if not os.path.exists(self.db_path):
            raise Exception(f"Database not found at {self.db_path}")
        return sqlite3.connect(self.db_path)
    
    def get_test_credentials(self, limit: int = None) -> List[Tuple[int, str, str, int]]:
        """Get RunSignUp credentials for testing"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        query = """
            SELECT timing_partner_id, principal, secret, partner_provider_credential_id
            FROM partner_provider_credentials 
            WHERE provider_id = 2 
            ORDER BY timing_partner_id
        """
        
        if limit:
            query += f" LIMIT {limit}"
            
        cursor.execute(query)
        credentials = cursor.fetchall()
        conn.close()
        
        logger.info(f"Found {len(credentials)} RunSignUp credential sets for testing")
        return credentials
    
    def test_database_connection(self) -> bool:
        """Test database connection"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM partner_provider_credentials WHERE provider_id = 2")
            count = cursor.fetchone()[0]
            conn.close()
            logger.info(f"✅ Database connection successful - Found {count} RunSignUp credentials")
            return True
        except Exception as e:
            logger.error(f"❌ Database connection failed: {e}")
            return False
    
    def get_database_baseline(self) -> Dict:
        """Get current database state as baseline"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        baseline = {}
        
        # Check if runsignup tables exist
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'runsignup_%'")
        tables = [row[0] for row in cursor.fetchall()]
        baseline['existing_tables'] = tables
        
        if 'runsignup_races' in tables:
            cursor.execute("""
                SELECT 
                    timing_partner_id,
                    COUNT(*) as race_count
                FROM runsignup_races 
                GROUP BY timing_partner_id
                ORDER BY timing_partner_id
            """)
            baseline['races_by_partner'] = dict(cursor.fetchall())
        else:
            baseline['races_by_partner'] = {}
        
        if 'runsignup_events' in tables:
            cursor.execute("""
                SELECT 
                    timing_partner_id,
                    COUNT(*) as event_count
                FROM runsignup_events 
                GROUP BY timing_partner_id
                ORDER BY timing_partner_id
            """)
            baseline['events_by_partner'] = dict(cursor.fetchall())
            
            # Get future events
            cursor.execute("""
                SELECT 
                    timing_partner_id,
                    COUNT(*) as future_event_count
                FROM runsignup_events 
                WHERE start_time > datetime('now')
                GROUP BY timing_partner_id
                ORDER BY timing_partner_id
            """)
            baseline['future_events_by_partner'] = dict(cursor.fetchall())
        else:
            baseline['events_by_partner'] = {}
            baseline['future_events_by_partner'] = {}
        
        if 'runsignup_participants' in tables:
            cursor.execute("""
                SELECT 
                    timing_partner_id,
                    COUNT(*) as participant_count
                FROM runsignup_participants 
                GROUP BY timing_partner_id
                ORDER BY timing_partner_id
            """)
            baseline['participants_by_partner'] = dict(cursor.fetchall())
        else:
            baseline['participants_by_partner'] = {}
        
        conn.close()
        
        logger.info("📊 Database Baseline:")
        logger.info(f"   • Existing tables: {baseline['existing_tables']}")
        logger.info(f"   • Races by partner: {baseline['races_by_partner']}")
        logger.info(f"   • Events by partner: {baseline['events_by_partner']}")
        logger.info(f"   • Future events by partner: {baseline['future_events_by_partner']}")
        logger.info(f"   • Participants by partner: {baseline['participants_by_partner']}")
        
        return baseline
    
    def test_full_sync_future_events(self, test_partner_limit: int = 2) -> Dict:
        """Test 1: Full syncs of future events for all credential sets"""
        logger.info("\n" + "="*80)
        logger.info("🧪 TEST 1: Full Sync of Future Events for All Credential Sets")
        logger.info("="*80)
        
        # Get baseline
        baseline = self.get_database_baseline()
        
        # Get test credentials (limit for testing)
        credentials = self.get_test_credentials(limit=test_partner_limit)
        
        test_results = {
            'timing_partners_tested': len(credentials),
            'partners_results': {},
            'future_events_found': 0,
            'total_participants_synced': 0,
            'errors': []
        }
        
        for timing_partner_id, principal, secret, credential_id in credentials:
            logger.info(f"\n🔍 Testing timing partner {timing_partner_id}")
            
            partner_results = {
                'timing_partner_id': timing_partner_id,
                'authentication': False,
                'races_found': 0,
                'future_events_found': 0,
                'participants_synced': 0,
                'sample_events': [],
                'errors': []
            }
            
            try:
                # Create adapter
                credentials_dict = {'principal': principal, 'secret': secret}
                adapter = RunSignUpAdapter(credentials_dict, timing_partner_id)
                
                # Test authentication
                if adapter.authenticate():
                    partner_results['authentication'] = True
                    logger.info(f"✅ Authentication successful for partner {timing_partner_id}")
                    
                    # Get all events (full sync)
                    provider_events = adapter.get_events()
                    
                    if provider_events:
                        # Filter for future events only
                        future_events = [e for e in provider_events if e.event_date and e.event_date > datetime.now()]
                        partner_results['future_events_found'] = len(future_events)
                        test_results['future_events_found'] += len(future_events)
                        
                        logger.info(f"📅 Found {len(provider_events)} total events, {len(future_events)} future events")
                        
                        # Collect sample events info
                        for event in future_events[:5]:  # Sample first 5 future events
                            event_info = {
                                'event_id': event.provider_event_id,
                                'event_name': event.event_name,
                                'event_date': str(event.event_date),
                                'location': f"{event.location_city}, {event.location_state}" if event.location_city else "Unknown"
                            }
                            partner_results['sample_events'].append(event_info)
                        
                        # Test participant sync for first few future events
                        events_to_test = future_events[:3] if len(future_events) > 3 else future_events
                        
                        for event in events_to_test:
                            race_data = event.raw_data.get('race', {})
                            event_data = event.raw_data.get('event', {})
                            race_id = race_data.get('race_id')
                            event_id = event_data.get('event_id')
                            
                            logger.info(f"🎯 Testing event: {event.event_name} (ID: {event_id})")
                            
                            # Get participants for this event
                            try:
                                provider_participants = adapter.get_participants(race_id, str(event_id))
                                participant_count = len(provider_participants)
                                partner_results['participants_synced'] += participant_count
                                
                                logger.info(f"✅ Event {event_id}: {participant_count} participants")
                                
                                # Sample participant data for verification
                                if provider_participants:
                                    sample_participant = provider_participants[0]
                                    logger.info(f"   Sample participant: {sample_participant.first_name} {sample_participant.last_name}")
                                    logger.info(f"   Bib: {sample_participant.bib_number or 'Not assigned'}")
                                    logger.info(f"   Email: {sample_participant.email or 'Not provided'}")
                                
                            except Exception as e:
                                error_msg = f"Error getting participants for event {event_id}: {str(e)}"
                                logger.error(f"❌ {error_msg}")
                                partner_results['errors'].append(error_msg)
                        
                        partner_results['races_found'] = len(set(e.raw_data.get('race', {}).get('race_id') for e in future_events))
                        
                    else:
                        logger.warning(f"⚠️  No events found for partner {timing_partner_id}")
                        
                else:
                    error_msg = f"Authentication failed for partner {timing_partner_id}"
                    logger.error(f"❌ {error_msg}")
                    partner_results['errors'].append(error_msg)
                    
            except Exception as e:
                error_msg = f"Error testing partner {timing_partner_id}: {str(e)}"
                logger.error(f"❌ {error_msg}")
                partner_results['errors'].append(error_msg)
                test_results['errors'].append(error_msg)
            
            test_results['partners_results'][timing_partner_id] = partner_results
            test_results['total_participants_synced'] += partner_results['participants_synced']
        
        logger.info(f"\n📊 TEST 1 RESULTS:")
        logger.info(f"   • Timing partners tested: {test_results['timing_partners_tested']}")
        logger.info(f"   • Future events found: {test_results['future_events_found']}")
        logger.info(f"   • Total participants synced: {test_results['total_participants_synced']}")
        logger.info(f"   • Errors: {len(test_results['errors'])}")
        
        test_results['baseline_before'] = baseline
        
        return test_results
    
    def test_incremental_sync(self, test_partner_id: int = None) -> Dict:
        """Test 2: Incremental sync (only modified records since last sync)"""
        logger.info("\n" + "="*80)
        logger.info("🧪 TEST 2: Incremental Sync (Modified Records Only)")
        logger.info("="*80)
        
        # Get one credential for detailed testing
        credentials = self.get_test_credentials(limit=1)
        if not credentials:
            return {'error': 'No credentials available for testing'}
        
        timing_partner_id, principal, secret, credential_id = credentials[0]
        
        logger.info(f"🔍 Testing incremental sync with timing partner {timing_partner_id}")
        
        test_results = {
            'timing_partner_id': timing_partner_id,
            'full_sync_results': {},
            'incremental_sync_results': {},
            'comparison': {},
            'errors': []
        }
        
        try:
            credentials_dict = {'principal': principal, 'secret': secret}
            adapter = RunSignUpAdapter(credentials_dict, timing_partner_id)
            
            if not adapter.authenticate():
                test_results['errors'].append("Authentication failed")
                return test_results
            
            logger.info("✅ Authentication successful")
            
            # STEP 1: Full sync to establish baseline
            logger.info("📊 Step 1: Full sync to establish baseline")
            
            full_events = adapter.get_events()
            test_results['full_sync_results']['total_events'] = len(full_events)
            
            # Get participants for first few events to establish baseline
            baseline_participants = {}
            future_events = [e for e in full_events if e.event_date and e.event_date > datetime.now()]
            
            logger.info(f"Found {len(future_events)} future events for baseline")
            
            for i, event in enumerate(future_events[:3]):  # Test with first 3 future events
                race_data = event.raw_data.get('race', {})
                event_data = event.raw_data.get('event', {})
                race_id = race_data.get('race_id')
                event_id = event_data.get('event_id')
                
                participants = adapter.get_participants(race_id, str(event_id))
                baseline_participants[event_id] = {
                    'count': len(participants),
                    'event_name': event.event_name,
                    'with_bibs': sum(1 for p in participants if p.bib_number),
                    'without_bibs': sum(1 for p in participants if not p.bib_number)
                }
                logger.info(f"Baseline: Event {event_id} ({event.event_name}) has {len(participants)} participants")
            
            test_results['full_sync_results']['participant_details'] = baseline_participants
            
            # STEP 2: Incremental sync 
            logger.info("📊 Step 2: Incremental sync with different time periods")
            
            # Use different time periods for incremental sync testing
            time_periods = [
                ('24 hours', timedelta(hours=24)),
                ('7 days', timedelta(days=7)),
                ('30 days', timedelta(days=30))
            ]
            
            incremental_results = {}
            
            for period_name, period_delta in time_periods:
                logger.info(f"🕐 Testing incremental sync for last {period_name}")
                last_modified_since = datetime.now() - period_delta
                
                incremental_events = adapter.get_events(last_modified_since=last_modified_since)
                
                incremental_participants = {}
                for event in incremental_events[:3]:  # Test with first 3 events
                    race_data = event.raw_data.get('race', {})
                    event_data = event.raw_data.get('event', {})
                    race_id = race_data.get('race_id')
                    event_id = event_data.get('event_id')
                    
                    participants = adapter.get_participants(race_id, str(event_id), last_modified_since=last_modified_since)
                    incremental_participants[event_id] = {
                        'count': len(participants),
                        'event_name': event.event_name,
                        'with_bibs': sum(1 for p in participants if p.bib_number),
                        'without_bibs': sum(1 for p in participants if not p.bib_number)
                    }
                    logger.info(f"Incremental ({period_name}): Event {event_id} has {len(participants)} modified participants")
                
                incremental_results[period_name] = {
                    'events': len(incremental_events),
                    'participants': incremental_participants
                }
            
            test_results['incremental_sync_results'] = incremental_results
            
            # STEP 3: Compare results
            logger.info("📊 Step 3: Comparing full vs incremental sync results")
            
            comparison = {
                'full_events': len(full_events),
                'future_events': len(future_events),
                'incremental_comparisons': {}
            }
            
            for period_name, results in incremental_results.items():
                comparison['incremental_comparisons'][period_name] = {
                    'events': results['events'],
                    'event_ratio': results['events'] / len(full_events) if len(full_events) > 0 else 0
                }
            
            test_results['comparison'] = comparison
            
            logger.info(f"📊 INCREMENTAL SYNC COMPARISON:")
            logger.info(f"   • Full sync events: {comparison['full_events']}")
            logger.info(f"   • Future events: {comparison['future_events']}")
            for period, comp in comparison['incremental_comparisons'].items():
                logger.info(f"   • {period} incremental: {comp['events']} events ({comp['event_ratio']:.2%})")
                
        except Exception as e:
            error_msg = f"Error in incremental sync test: {str(e)}"
            logger.error(f"❌ {error_msg}")
            test_results['errors'].append(error_msg)
        
        return test_results
    
    def test_bib_assignment_triggers(self, test_partner_id: int = None) -> Dict:
        """Test 3: Bib assignment triggers (when bibs are assigned in RunSignUp)"""
        logger.info("\n" + "="*80)
        logger.info("🧪 TEST 3: Bib Assignment Triggers")
        logger.info("="*80)
        
        # Get one credential for testing
        credentials = self.get_test_credentials(limit=1)
        if not credentials:
            return {'error': 'No credentials available for testing'}
        
        timing_partner_id, principal, secret, credential_id = credentials[0]
        
        logger.info(f"🔍 Testing bib assignment triggers with timing partner {timing_partner_id}")
        
        test_results = {
            'timing_partner_id': timing_partner_id,
            'participants_with_bibs': 0,
            'participants_without_bibs': 0,
            'recent_bib_assignments': 0,
            'events_tested': 0,
            'bib_statistics': {},
            'sample_bib_data': [],
            'errors': []
        }
        
        try:
            credentials_dict = {'principal': principal, 'secret': secret}
            adapter = RunSignUpAdapter(credentials_dict, timing_partner_id)
            
            if not adapter.authenticate():
                test_results['errors'].append("Authentication failed")
                return test_results
            
            logger.info("✅ Authentication successful")
            
            # Get recent events to check for bib assignments
            events = adapter.get_events()
            future_events = [e for e in events if e.event_date and e.event_date > datetime.now()][:5]  # Test with 5 future events
            
            logger.info(f"🎯 Testing bib assignments in {len(future_events)} future events")
            
            event_bib_stats = {}
            
            for event in future_events:
                race_data = event.raw_data.get('race', {})
                event_data = event.raw_data.get('event', {})
                race_id = race_data.get('race_id')
                event_id = event_data.get('event_id')
                event_name = event_data.get('name', 'Unknown Event')
                
                logger.info(f"📋 Checking event {event_id}: {event_name}")
                
                # Get all participants for this event
                participants = adapter.get_participants(race_id, str(event_id))
                test_results['events_tested'] += 1
                
                participants_with_bibs = 0
                participants_without_bibs = 0
                bib_numbers = []
                sample_participants = []
                
                for participant in participants:
                    if participant.bib_number:
                        participants_with_bibs += 1
                        bib_numbers.append(participant.bib_number)
                        if len(sample_participants) < 3:  # Collect sample participants
                            sample_participants.append({
                                'name': f"{participant.first_name} {participant.last_name}",
                                'bib': participant.bib_number,
                                'registration_id': participant.provider_participant_id,
                                'email': participant.email
                            })
                    else:
                        participants_without_bibs += 1
                
                event_stats = {
                    'event_name': event_name,
                    'event_date': str(event.event_date),
                    'total_participants': len(participants),
                    'with_bibs': participants_with_bibs,
                    'without_bibs': participants_without_bibs,
                    'bib_assignment_rate': participants_with_bibs / len(participants) if len(participants) > 0 else 0,
                    'sample_participants': sample_participants,
                    'bib_range': {
                        'min': min(bib_numbers) if bib_numbers else None,
                        'max': max(bib_numbers) if bib_numbers else None,
                        'count': len(bib_numbers)
                    }
                }
                
                event_bib_stats[event_id] = event_stats
                
                test_results['participants_with_bibs'] += participants_with_bibs
                test_results['participants_without_bibs'] += participants_without_bibs
                test_results['sample_bib_data'].extend(sample_participants)
                
                logger.info(f"   • Total participants: {len(participants)}")
                logger.info(f"   • Participants with bibs: {participants_with_bibs}")
                logger.info(f"   • Participants without bibs: {participants_without_bibs}")
                logger.info(f"   • Bib assignment rate: {event_stats['bib_assignment_rate']:.1%}")
                
                if bib_numbers:
                    logger.info(f"   • Bib range: {min(bib_numbers)} - {max(bib_numbers)} ({len(bib_numbers)} total)")
                
                if sample_participants:
                    logger.info("   • Sample bib assignments:")
                    for sample in sample_participants:
                        logger.info(f"     - {sample['name']}: Bib #{sample['bib']}")
            
            test_results['bib_statistics'] = event_bib_stats
            
            # Test incremental sync to see if bib assignments trigger updates
            logger.info("🔄 Testing incremental sync for recent bib assignments")
            
            # Use different time periods to check for recent modifications
            time_periods = [('24 hours', 24), ('48 hours', 48), ('7 days', 7*24)]
            
            for period_name, hours in time_periods:
                logger.info(f"📅 Checking for modifications in last {period_name}")
                last_modified_since = datetime.now() - timedelta(hours=hours)
                
                recent_count = 0
                recent_with_bibs = 0
                
                for event in future_events[:2]:  # Test with first 2 events
                    race_data = event.raw_data.get('race', {})
                    event_data = event.raw_data.get('event', {})
                    race_id = race_data.get('race_id')
                    event_id = event_data.get('event_id')
                    
                    # Get recently modified participants
                    recent_participants = adapter.get_participants(race_id, str(event_id), last_modified_since=last_modified_since)
                    
                    event_recent_with_bibs = sum(1 for p in recent_participants if p.bib_number)
                    recent_count += len(recent_participants)
                    recent_with_bibs += event_recent_with_bibs
                    
                    logger.info(f"   • Event {event_id}: {len(recent_participants)} recently modified, {event_recent_with_bibs} with bibs")
                
                if period_name == '48 hours':  # Store the 48-hour result as main metric
                    test_results['recent_bib_assignments'] = recent_with_bibs
            
            # Calculate overall statistics
            total_participants = test_results['participants_with_bibs'] + test_results['participants_without_bibs']
            bib_assignment_rate = test_results['participants_with_bibs'] / total_participants if total_participants > 0 else 0
            
            logger.info(f"\n📊 BIB ASSIGNMENT TEST RESULTS:")
            logger.info(f"   • Events tested: {test_results['events_tested']}")
            logger.info(f"   • Total participants checked: {total_participants}")
            logger.info(f"   • Participants with bibs: {test_results['participants_with_bibs']}")
            logger.info(f"   • Participants without bibs: {test_results['participants_without_bibs']}")
            logger.info(f"   • Overall bib assignment rate: {bib_assignment_rate:.2%}")
            logger.info(f"   • Recent bib assignments (48h): {test_results['recent_bib_assignments']}")
            
            test_results['bib_assignment_rate'] = bib_assignment_rate
            test_results['total_participants'] = total_participants
            
        except Exception as e:
            error_msg = f"Error in bib assignment test: {str(e)}"
            logger.error(f"❌ {error_msg}")
            test_results['errors'].append(error_msg)
        
        return test_results
    
    def run_all_tests(self, test_partner_limit: int = 2) -> Dict:
        """Run all comprehensive tests"""
        logger.info("\n" + "🧪" * 40)
        logger.info("🚀 STARTING COMPREHENSIVE RUNSIGNUP INTEGRATION TESTS (SQLite)")
        logger.info("🧪" * 40)
        
        # First test database connection
        if not self.test_database_connection():
            logger.error("❌ Database connection test failed. Aborting tests.")
            return {'error': 'Database connection failed'}
        
        start_time = datetime.now()
        
        # Run Test 1: Full Sync
        logger.info("Starting Test 1: Full Sync...")
        self.test_results['full_sync_test'] = self.test_full_sync_future_events(test_partner_limit)
        
        # Run Test 2: Incremental Sync
        logger.info("Starting Test 2: Incremental Sync...")
        self.test_results['incremental_sync_test'] = self.test_incremental_sync()
        
        # Run Test 3: Bib Assignment
        logger.info("Starting Test 3: Bib Assignment...")
        self.test_results['bib_assignment_test'] = self.test_bib_assignment_triggers()
        
        # Generate summary
        duration = (datetime.now() - start_time).total_seconds()
        
        summary = {
            'test_start_time': start_time.isoformat(),
            'test_duration_seconds': duration,
            'tests_run': 3,
            'database_type': 'SQLite',
            'database_path': self.db_path,
            'test_success': {
                'full_sync': len(self.test_results['full_sync_test'].get('errors', [])) == 0,
                'incremental_sync': len(self.test_results['incremental_sync_test'].get('errors', [])) == 0,
                'bib_assignment': len(self.test_results['bib_assignment_test'].get('errors', [])) == 0
            }
        }
        
        self.test_results['summary'] = summary
        
        # Write results to file
        with open('test_results_comprehensive_sqlite.json', 'w') as f:
            json.dump(self.test_results, f, indent=2, default=str)
        
        # Final summary
        logger.info("\n" + "🎉" * 40)
        logger.info("🎉 COMPREHENSIVE TESTS COMPLETE!")
        logger.info("🎉" * 40)
        logger.info(f"⏱️  Total duration: {duration:.2f} seconds")
        logger.info(f"📊 Test Results:")
        logger.info(f"   • Full Sync Test: {'✅ PASS' if summary['test_success']['full_sync'] else '❌ FAIL'}")
        logger.info(f"   • Incremental Sync Test: {'✅ PASS' if summary['test_success']['incremental_sync'] else '❌ FAIL'}")
        logger.info(f"   • Bib Assignment Test: {'✅ PASS' if summary['test_success']['bib_assignment'] else '❌ FAIL'}")
        logger.info(f"📄 Detailed results saved to: test_results_comprehensive_sqlite.json")
        
        return self.test_results

def main():
    """Main test execution"""
    import argparse
    
    parser = argparse.ArgumentParser(description='RunSignUp Comprehensive Integration Tests (SQLite)')
    parser.add_argument('--test', choices=['full', 'incremental', 'bib', 'all'], 
                       default='all', help='Which test to run')
    parser.add_argument('--partner-limit', type=int, default=2, 
                       help='Limit number of timing partners for testing')
    parser.add_argument('--partner-id', type=int, 
                       help='Specific timing partner ID to test')
    
    args = parser.parse_args()
    
    tester = RunSignUpComprehensiveTest()
    
    if args.test == 'full':
        result = tester.test_full_sync_future_events(args.partner_limit)
        print(f"\nTest completed. Check logs for details.")
    elif args.test == 'incremental':
        result = tester.test_incremental_sync(args.partner_id)
        print(f"\nTest completed. Check logs for details.")
    elif args.test == 'bib':
        result = tester.test_bib_assignment_triggers(args.partner_id)
        print(f"\nTest completed. Check logs for details.")
    else:
        result = tester.run_all_tests(args.partner_limit)
        print(f"\nAll tests completed. Check test_results_comprehensive_sqlite.json for detailed results.")

if __name__ == "__main__":
    main() 