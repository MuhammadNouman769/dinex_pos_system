from apps.orders.models import Table


class TableSelector:
    """
    Table Selector with advanced filtering
    """
    
    @staticmethod
    def get_all_tables(location_id=None, only_active=True):
        """
        Get all tables with optional location filter
        """
        queryset = Table.objects.all()
        
        if location_id:
            queryset = queryset.filter(location_id=location_id)
        
        if only_active:
            queryset = queryset.filter(is_active=True)
        
        return queryset
    
    @staticmethod
    def get_available_tables(location_id):
        """
        Get available tables at a location
        """
        return Table.objects.filter(
            location_id=location_id,
            status=Table.TableStatus.AVAILABLE,
            is_active=True,
            is_deleted=False
        )
    
    @staticmethod
    def get_occupied_tables(location_id):
        """
        Get occupied tables at a location
        """
        return Table.objects.filter(
            location_id=location_id,
            status=Table.TableStatus.OCCUPIED,
            is_active=True,
            is_deleted=False
        )
    
    @staticmethod
    def get_table_by_number(location_id, table_number):
        """
        Get table by number at a location
        """
        return Table.objects.get(
            location_id=location_id,
            table_number=table_number,
            is_deleted=False
        )
    
    @staticmethod
    def search_tables(location_id, search_term):
        """
        Search tables by number
        """
        return Table.objects.filter(
            location_id=location_id,
            is_deleted=False
        ).filter(
            table_number__icontains=search_term
        )