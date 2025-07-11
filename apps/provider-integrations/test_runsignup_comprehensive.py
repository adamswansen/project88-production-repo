#!/usr/bin/env python3
"""
Comprehensive RunSignUp Integration Testing Script

Tests:
1. Full syncs of future events for all credential sets
2. Incremental syncs (only modified records since last sync)  
3. Bib assignment triggers (when bibs are assigned in RunSignUp)
"""

import sys
import os
import psycopg2
import psycopg2.extras
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
    """Comprehensive RunSignUp integration testing"""
    
    def __init__(self):
        # PostgreSQL connection using environment variables with fallback defaults
        self.db_config = {
            'host': os.getenv('DB_HOST', 'localhost'),
            'database': os.getenv('DB_NAME', 'project88_myappdb'),
            'user': os.getenv('DB_USER', 'project88_myappuser'),
            'password': os.getenv('DB_PASSWORD', 'puctuq-cefwyq-3boqRe'),
            'port': int(os.getenv('DB_PORT', '5432'))
        }
        
        self.test_results = {
            'full_sync_test': {},
            'incremental_sync_test': {},
            'bib_assignment_test': {},
            'summary': {}
        }
        
    def get_connection(self):
        """Get PostgreSQL database connection"""
        return psycopg2.connect(**self.db_config)
    
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
    
    def get_database_baseline(self) -> Dict:
        """Get current database state as baseline"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        baseline = {}
        
        # Get counts by timing partner
        cursor.execute("""
            SELECT 
                timing_partner_id,
                COUNT(*) as race_count
            FROM runsignup_races 
            GROUP BY timing_partner_id
            ORDER BY timing_partner_id
        """)
        baseline['races_by_partner'] = dict(cursor.fetchall())
        
        cursor.execute("""
            SELECT 
                timing_partner_id,
                COUNT(*) as event_count
            FROM runsignup_events 
            GROUP BY timing_partner_id
            ORDER BY timing_partner_id
        """)
        baseline['events_by_partner'] = dict(cursor.fetchall())
        
        cursor.execute("""
            SELECT 
                timing_partner_id,
                COUNT(*) as participant_count
            FROM runsignup_participants 
            GROUP BY timing_partner_id
            ORDER BY timing_partner_id
        """)
        baseline['participants_by_partner'] = dict(cursor.fetchall())
        
        # Get future events (events after today)
        cursor.execute("""
            SELECT 
                timing_partner_id,
                COUNT(*) as future_event_count
            FROM runsignup_events 
            WHERE start_time > NOW()
            GROUP BY timing_partner_id
            ORDER BY timing_partner_id
        """)
        baseline['future_events_by_partner'] = dict(cursor.fetchall())
        
        # Get recent sync history
        cursor.execute("""
            SELECT 
                provider_id,
                MAX(sync_time) as last_sync_time,
                COUNT(*) as sync_count
            FROM sync_history 
            WHERE provider_id = 2
            GROUP BY provider_id
        """)
        sync_data = cursor.fetchone()
        baseline['last_sync_time'] = sync_data[1] if sync_data else None
        baseline['total_sync_count'] = sync_data[2] if sync_data else 0
        
        conn.close()
        
        logger.info("📊 Database Baseline:")
        logger.info(f"   • Races by partner: {baseline['races_by_partner']}")
        logger.info(f"   • Events by partner: {baseline['events_by_partner']}")
        logger.info(f"   • Future events by partner: {baseline['future_events_by_partner']}")
        logger.info(f"   • Participants by partner: {baseline['participants_by_partner']}")
        logger.info(f"   • Last sync time: {baseline['last_sync_time']}")
        
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
                        
                        # Group events by race for efficient processing
                        races_with_events = {}
                        for event in future_events:
                            race_data = event.raw_data.get('race', {})
                            race_id = race_data.get('race_id')
                            if race_id:
                                if race_id not in races_with_events:
                                    races_with_events[race_id] = {
                                        'race': race_data,
                                        'events': []
                                    }
                                races_with_events[race_id]['events'].append(event.raw_data.get('event', {}))
                        
                        partner_results['races_found'] = len(races_with_events)
                        
                        # Connect to database for this partner
                        conn = self.get_connection()
                        
                        try:
                            for race_id, race_with_events in races_with_events.items():
                                race_data = race_with_events['race']
                                events = race_with_events['events']
                                
                                # Store race
                                adapter.store_race(race_data, conn)
                                
                                # Process events
                                for event_data in events:
                                    event_id = event_data['event_id']
                                    
                                    # Store event
                                    adapter.store_event(event_data, race_id, conn)
                                    
                                    # Get participants for this event
                                    provider_participants = adapter.get_participants(race_id, str(event_id))
                                    
                                    if provider_participants:
                                        participant_count = len(provider_participants)
                                        partner_results['participants_synced'] += participant_count
                                        
                                        for provider_participant in provider_participants:
                                            participant_data = provider_participant.raw_data
                                            adapter.store_participant(participant_data, race_id, event_id, conn)
                                        
                                        logger.info(f"✅ Synced {participant_count} participants for future event {event_id}")
                            
                            # Commit changes
                            conn.commit()
                            logger.info(f"✅ Committed changes for partner {timing_partner_id}")
                            
                        finally:
                            conn.close()
                            
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
        
        # Compare with baseline
        new_baseline = self.get_database_baseline()
        
        logger.info(f"\n📊 TEST 1 RESULTS:")
        logger.info(f"   • Timing partners tested: {test_results['timing_partners_tested']}")
        logger.info(f"   • Future events found: {test_results['future_events_found']}")
        logger.info(f"   • Total participants synced: {test_results['total_participants_synced']}")
        logger.info(f"   • Errors: {len(test_results['errors'])}")
        
        test_results['baseline_before'] = baseline
        test_results['baseline_after'] = new_baseline
        
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
        if test_partner_id:
            # Find specific partner if requested
            all_credentials = self.get_test_credentials()
            target_cred = next((c for c in all_credentials if c[0] == test_partner_id), None)
            if target_cred:
                timing_partner_id, principal, secret, credential_id = target_cred
        
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
            baseline_time = datetime.now()
            
            full_events = adapter.get_events()
            test_results['full_sync_results']['total_events'] = len(full_events)
            
            # Get participants for first few events to establish baseline
            baseline_participants = {}
            for i, event in enumerate(full_events[:3]):  # Test with first 3 events
                race_data = event.raw_data.get('race', {})
                event_data = event.raw_data.get('event', {})
                race_id = race_data.get('race_id')
                event_id = event_data.get('event_id')
                
                participants = adapter.get_participants(race_id, str(event_id))
                baseline_participants[event_id] = len(participants)
                logger.info(f"Baseline: Event {event_id} has {len(participants)} participants")
            
            test_results['full_sync_results']['participant_counts'] = baseline_participants
            
            # STEP 2: Incremental sync (simulate time passing)
            logger.info("📊 Step 2: Incremental sync with last_modified_since")
            
            # Use a recent time for incremental sync (last 24 hours)
            last_modified_since = datetime.now() - timedelta(hours=24)
            
            incremental_events = adapter.get_events(last_modified_since=last_modified_since)
            test_results['incremental_sync_results']['total_events'] = len(incremental_events)
            
            # Get participants with incremental sync
            incremental_participants = {}
            for event in incremental_events[:3]:  # Test with first 3 events
                race_data = event.raw_data.get('race', {})
                event_data = event.raw_data.get('event', {})
                race_id = race_data.get('race_id')
                event_id = event_data.get('event_id')
                
                participants = adapter.get_participants(race_id, str(event_id), last_modified_since=last_modified_since)
                incremental_participants[event_id] = len(participants)
                logger.info(f"Incremental: Event {event_id} has {len(participants)} modified participants")
            
            test_results['incremental_sync_results']['participant_counts'] = incremental_participants
            
            # STEP 3: Compare results
            logger.info("📊 Step 3: Comparing full vs incremental sync results")
            
            comparison = {
                'events_full_vs_incremental': {
                    'full': len(full_events),
                    'incremental': len(incremental_events),
                    'ratio': len(incremental_events) / len(full_events) if len(full_events) > 0 else 0
                },
                'participants_comparison': {}
            }
            
            for event_id in baseline_participants:
                if event_id in incremental_participants:
                    comparison['participants_comparison'][event_id] = {
                        'full': baseline_participants[event_id],
                        'incremental': incremental_participants[event_id],
                        'ratio': incremental_participants[event_id] / baseline_participants[event_id] if baseline_participants[event_id] > 0 else 0
                    }
            
            test_results['comparison'] = comparison
            
            logger.info(f"📊 INCREMENTAL SYNC COMPARISON:")
            logger.info(f"   • Full sync events: {comparison['events_full_vs_incremental']['full']}")
            logger.info(f"   • Incremental events: {comparison['events_full_vs_incremental']['incremental']}")
            logger.info(f"   • Incremental ratio: {comparison['events_full_vs_incremental']['ratio']:.2%}")
            
            for event_id, comp in comparison['participants_comparison'].items():
                logger.info(f"   • Event {event_id}: {comp['full']} → {comp['incremental']} participants ({comp['ratio']:.2%})")
                
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
        if test_partner_id:
            all_credentials = self.get_test_credentials()
            target_cred = next((c for c in all_credentials if c[0] == test_partner_id), None)
            if target_cred:
                timing_partner_id, principal, secret, credential_id = target_cred
        
        logger.info(f"🔍 Testing bib assignment triggers with timing partner {timing_partner_id}")
        
        test_results = {
            'timing_partner_id': timing_partner_id,
            'participants_with_bibs': 0,
            'participants_without_bibs': 0,
            'recent_bib_assignments': 0,
            'sample_participants': [],
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
            
            for event in future_events:
                race_data = event.raw_data.get('race', {})
                event_data = event.raw_data.get('event', {})
                race_id = race_data.get('race_id')
                event_id = event_data.get('event_id')
                
                logger.info(f"📋 Checking event {event_id}: {event_data.get('name')}")
                
                # Get all participants for this event
                participants = adapter.get_participants(race_id, str(event_id))
                
                participants_with_bibs = 0
                participants_without_bibs = 0
                sample_bibs = []
                
                for participant in participants:
                    if participant.bib_number:
                        participants_with_bibs += 1
                        if len(sample_bibs) < 5:  # Collect sample bib numbers
                            sample_bibs.append({
                                'name': f"{participant.first_name} {participant.last_name}",
                                'bib': participant.bib_number,
                                'registration_id': participant.provider_participant_id
                            })
                    else:
                        participants_without_bibs += 1
                
                test_results['participants_with_bibs'] += participants_with_bibs
                test_results['participants_without_bibs'] += participants_without_bibs
                test_results['sample_participants'].extend(sample_bibs)
                
                logger.info(f"   • Participants with bibs: {participants_with_bibs}")
                logger.info(f"   • Participants without bibs: {participants_without_bibs}")
                
                if sample_bibs:
                    logger.info("   • Sample bib assignments:")
                    for sample in sample_bibs:
                        logger.info(f"     - {sample['name']}: Bib #{sample['bib']}")
            
            # Test incremental sync to see if bib assignments trigger updates
            logger.info("🔄 Testing incremental sync for recent bib assignments")
            
            # Use last 48 hours to catch recent bib assignments
            last_modified_since = datetime.now() - timedelta(hours=48)
            
            for event in future_events[:2]:  # Test with first 2 events
                race_data = event.raw_data.get('race', {})
                event_data = event.raw_data.get('event', {})
                race_id = race_data.get('race_id')
                event_id = event_data.get('event_id')
                
                # Get recently modified participants
                recent_participants = adapter.get_participants(race_id, str(event_id), last_modified_since=last_modified_since)
                
                recent_with_bibs = sum(1 for p in recent_participants if p.bib_number)
                test_results['recent_bib_assignments'] += recent_with_bibs
                
                logger.info(f"📅 Event {event_id}: {len(recent_participants)} recently modified, {recent_with_bibs} with bibs")
            
            # Calculate statistics
            total_participants = test_results['participants_with_bibs'] + test_results['participants_without_bibs']
            bib_assignment_rate = test_results['participants_with_bibs'] / total_participants if total_participants > 0 else 0
            
            logger.info(f"\n📊 BIB ASSIGNMENT TEST RESULTS:")
            logger.info(f"   • Total participants checked: {total_participants}")
            logger.info(f"   • Participants with bibs: {test_results['participants_with_bibs']}")
            logger.info(f"   • Participants without bibs: {test_results['participants_without_bibs']}")
            logger.info(f"   • Bib assignment rate: {bib_assignment_rate:.2%}")
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
        logger.info("🚀 STARTING COMPREHENSIVE RUNSIGNUP INTEGRATION TESTS")
        logger.info("🧪" * 40)
        
        start_time = datetime.now()
        
        # Run Test 1: Full Sync
        self.test_results['full_sync_test'] = self.test_full_sync_future_events(test_partner_limit)
        
        # Run Test 2: Incremental Sync
        self.test_results['incremental_sync_test'] = self.test_incremental_sync()
        
        # Run Test 3: Bib Assignment
        self.test_results['bib_assignment_test'] = self.test_bib_assignment_triggers()
        
        # Generate summary
        duration = (datetime.now() - start_time).total_seconds()
        
        summary = {
            'test_start_time': start_time.isoformat(),
            'test_duration_seconds': duration,
            'tests_run': 3,
            'test_success': {
                'full_sync': len(self.test_results['full_sync_test'].get('errors', [])) == 0,
                'incremental_sync': len(self.test_results['incremental_sync_test'].get('errors', [])) == 0,
                'bib_assignment': len(self.test_results['bib_assignment_test'].get('errors', [])) == 0
            }
        }
        
        self.test_results['summary'] = summary
        
        # Write results to file
        with open('test_results_comprehensive.json', 'w') as f:
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
        logger.info(f"📄 Detailed results saved to: test_results_comprehensive.json")
        
        return self.test_results

def main():
    """Main test execution"""
    import argparse
    
    parser = argparse.ArgumentParser(description='RunSignUp Comprehensive Integration Tests')
    parser.add_argument('--test', choices=['full', 'incremental', 'bib', 'all'], 
                       default='all', help='Which test to run')
    parser.add_argument('--partner-limit', type=int, default=2, 
                       help='Limit number of timing partners for testing')
    parser.add_argument('--partner-id', type=int, 
                       help='Specific timing partner ID to test')
    
    args = parser.parse_args()
    
    tester = RunSignUpComprehensiveTest()
    
    if args.test == 'full':
        tester.test_full_sync_future_events(args.partner_limit)
    elif args.test == 'incremental':
        tester.test_incremental_sync(args.partner_id)
    elif args.test == 'bib':
        tester.test_bib_assignment_triggers(args.partner_id)
    else:
        tester.run_all_tests(args.partner_limit)

if __name__ == "__main__":
    main() 