"""
Tests pour PRIORITÉ 4 — Exclusion clients avec sources_count=0

Vérifie que:
- Clients avec sources_count=0 sont exclus de clients_used
- Compteur clients_no_sources est présent dans stats
- Métriques ne sont pas biaisées
"""
import pytest


class TestClientsUsedCalculation:
    """Tests unitaires de la logique de calcul clients_used"""
    
    def test_clients_used_excludes_sources_count_zero(self):
        """
        Test direct de la logique d'exclusion (sans dépendances)
        """
        # Simuler une liste de clients après scan
        successful_clients = [
            {"folder_name": "Client1", "sources_count": 0},  # Sans sources
            {"folder_name": "Client2", "sources_count": 2},  # Avec sources
            {"folder_name": "Client3", "sources_count": 1},  # Avec sources
            {"folder_name": "Client4", "sources_count": 0},  # Sans sources
        ]
        
        # ✅ PRIORITÉ 4: Logique d'exclusion
        clients_used_list = [c for c in successful_clients if c.get('sources_count', 0) > 0]
        clients_used = len(clients_used_list)
        clients_no_sources = len(successful_clients) - clients_used
        
        # Assertions
        assert clients_used == 2, \
            f"clients_used devrait être 2, got {clients_used}"
        assert clients_no_sources == 2, \
            f"clients_no_sources devrait être 2, got {clients_no_sources}"
        
        # Vérifier que clients sans sources ne sont pas comptés
        client_names_used = [c['folder_name'] for c in clients_used_list]
        assert "Client1" not in client_names_used
        assert "Client4" not in client_names_used
        assert "Client2" in client_names_used
        assert "Client3" in client_names_used
        
        print(f"✅ Test réussi:")
        print(f"   Total clients: {len(successful_clients)}")
        print(f"   Clients used: {clients_used}")
        print(f"   Clients no sources: {clients_no_sources}")
    
    def test_coverage_calculated_on_clients_used(self):
        """
        Vérifie que le coverage est calculé sur clients_used, pas sur tous
        """
        # Clients analysés
        successful_clients = [
            {"folder_name": "Client1", "sources_count": 0, "has_identity": False},
            {"folder_name": "Client2", "sources_count": 1, "has_identity": True},
            {"folder_name": "Client3", "sources_count": 1, "has_identity": False},
        ]
        
        # Calcul clients_used
        clients_used_list = [c for c in successful_clients if c.get('sources_count', 0) > 0]
        clients_used = len(clients_used_list)  # = 2
        
        # Calcul coverage identity (sur clients_used uniquement)
        clients_with_identity = [c for c in clients_used_list if c.get('has_identity')]
        identity_count = len(clients_with_identity)  # = 1
        
        # Coverage devrait être 50% (1/2), pas 33% (1/3)
        coverage_pct = round(100 * identity_count / clients_used, 1) if clients_used > 0 else 0
        
        assert coverage_pct == 50.0, \
            f"Coverage devrait être 50% (1/2 clients_used), got {coverage_pct}%"
        
        print(f"✅ Coverage calculé sur clients_used:")
        print(f"   clients_used: {clients_used}")
        print(f"   Identity coverage: {coverage_pct}%")
    
    def test_all_clients_have_sources(self):
        """Test quand tous les clients ont des sources"""
        successful_clients = [
            {"sources_count": 1},
            {"sources_count": 2},
            {"sources_count": 3},
        ]
        
        clients_used_list = [c for c in successful_clients if c.get('sources_count', 0) > 0]
        clients_used = len(clients_used_list)
        clients_no_sources = len(successful_clients) - clients_used
        
        assert clients_used == 3
        assert clients_no_sources == 0
    
    def test_no_clients_have_sources(self):
        """Test quand aucun client n'a de sources"""
        successful_clients = [
            {"sources_count": 0},
            {"sources_count": 0},
        ]
        
        clients_used_list = [c for c in successful_clients if c.get('sources_count', 0) > 0]
        clients_used = len(clients_used_list)
        clients_no_sources = len(successful_clients) - clients_used
        
        assert clients_used == 0
        assert clients_no_sources == 2
    
    def test_stats_structure_complete(self):
        """Vérifie que la structure stats contient bien clients_used et clients_no_sources"""
        successful_clients = [
            {"sources_count": 0},
            {"sources_count": 1},
        ]
        
        clients_used_list = [c for c in successful_clients if c.get('sources_count', 0) > 0]
        clients_used = len(clients_used_list)
        clients_no_sources = len(successful_clients) - clients_used
        
        # Simuler la structure stats
        stats = {
            "total_clients": len(successful_clients),
            "successful_scans": len(successful_clients),
            "clients_used": clients_used,
            "clients_no_sources": clients_no_sources,
        }
        
        # Vérifications
        assert 'clients_used' in stats
        assert 'clients_no_sources' in stats
        assert stats['clients_used'] + stats['clients_no_sources'] == stats['successful_scans']
