"""
Paint Formulation AI - Recipe Optimizer (Inverse Design)
=========================================================
Optimizes ingredient ratios to achieve target paint properties.

Uses scipy.optimize.differential_evolution for global optimization
to find recipes that match user-specified targets like:
- "Gloss: 90 GU"
- "Viscosity: 2000 cP"
- "Opacity: 95%"

This is "inverse design" - instead of predicting properties from a recipe,
we find a recipe that produces desired properties.
"""

import numpy as np
from typing import Dict, List, Any, Optional, Callable, Tuple
import logging
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class OptimizationDirection(Enum):
    """Optimization direction for a target."""
    MAXIMIZE = 'max'
    MINIMIZE = 'min'
    TARGET = 'target'  # Match exact value


@dataclass
class OptimizationTarget:
    """A single optimization target."""
    property_name: str
    target_value: float
    weight: float = 1.0
    direction: OptimizationDirection = OptimizationDirection.TARGET
    tolerance: float = 0.05  # 5% tolerance


@dataclass
class OptimizationResult:
    """Result of recipe optimization."""
    success: bool
    recipe: List[Dict]
    predicted_properties: Dict[str, float]
    optimization_score: float
    iterations: int
    message: str


class RecipeOptimizer:
    """
    Inverse design optimizer using differential evolution.
    
    Finds optimal ingredient ratios to achieve target properties
    by iteratively querying the ML model with different recipes.
    
    Example:
        optimizer = RecipeOptimizer(predictor, available_materials)
        result = optimizer.optimize(
            targets={'gloss': 90, 'viscosity': 2000},
            constraints={'max_cost': 50}
        )
    """
    
    # Default optimization parameters
    DEFAULT_OPT_PARAMS = {
        'maxiter': 100,
        'popsize': 15,
        'mutation': (0.5, 1.0),
        'recombination': 0.7,
        'seed': 42,
        'polish': True,
        'workers': 1,  # -1 for parallel
    }
    
    def __init__(
        self,
        predictor,
        available_materials: List[Dict],
        material_lookup: Callable = None
    ):
        """
        Initialize the recipe optimizer.
        
        Args:
            predictor: XGBoostPredictor or similar model with predict_properties method
            available_materials: List of available materials with properties
            material_lookup: Optional callback to get material details
        """
        self.predictor = predictor
        self.materials = available_materials
        self.material_lookup = material_lookup
        
        # Group materials by category for structured optimization
        self.materials_by_category = self._group_by_category()
    
    def _group_by_category(self) -> Dict[str, List[Dict]]:
        """Group materials by their category."""
        groups = {}
        
        for mat in self.materials:
            cat = mat.get('category', mat.get('material_category', 'other')).lower()
            
            # Simplify to main categories
            if any(k in cat for k in ['binder', 'resin', 'polymer']):
                group = 'binder'
            elif any(k in cat for k in ['pigment', 'filler', 'extender']):
                group = 'pigment'
            elif any(k in cat for k in ['solvent', 'thinner', 'water']):
                group = 'solvent'
            else:
                group = 'additive'
            
            if group not in groups:
                groups[group] = []
            groups[group].append(mat)
        
        return groups
    
    def optimize(
        self,
        targets: Dict[str, Any],
        constraints: Dict = None,
        optimization_params: Dict = None,
        fixed_materials: List[Dict] = None
    ) -> OptimizationResult:
        """
        Optimize recipe to match target properties.
        
        Args:
            targets: Target properties. Format:
                {'gloss': 90} or
                {'gloss': {'value': 90, 'weight': 1.5, 'direction': 'max'}}
            constraints: Optimization constraints:
                - 'max_cost': Maximum cost per kg
                - 'min_solid_content': Minimum solid content %
                - 'max_voc': Maximum VOC g/L
                - 'required_categories': ['binder', 'pigment', ...]
            optimization_params: Override default scipy.optimize parameters
            fixed_materials: materials that must be in the recipe
            
        Returns:
            OptimizationResult with optimized recipe
        """
        try:
            from scipy.optimize import differential_evolution
        except ImportError:
            return OptimizationResult(
                success=False,
                recipe=[],
                predicted_properties={},
                optimization_score=0,
                iterations=0,
                message='scipy not installed. Run: pip install scipy'
            )
        
        # Parse targets
        parsed_targets = self._parse_targets(targets)
        
        if not parsed_targets:
            return OptimizationResult(
                success=False,
                recipe=[],
                predicted_properties={},
                optimization_score=0,
                iterations=0,
                message='No valid targets specified'
            )
        
        # Setup constraints
        constraints = constraints or {}
        
        # Determine materials to optimize with
        opt_materials = self._select_materials_for_optimization(constraints)
        
        if len(opt_materials) < 2:
            return OptimizationResult(
                success=False,
                recipe=[],
                predicted_properties={},
                optimization_score=0,
                iterations=0,
                message='Not enough materials available for optimization'
            )
        
        n_materials = len(opt_materials)
        logger.info(f"Optimizing with {n_materials} materials for targets: {list(targets.keys())}")
        
        # Define bounds: each material can be 0-100%
        bounds = [(0, 100) for _ in range(n_materials)]
        
        # Track iterations
        iteration_count = [0]
        
        # Objective function
        def objective(amounts):
            iteration_count[0] += 1
            
            # Amounts must sum to reasonable total
            total = sum(amounts)
            if total < 10:
                return 1e6  # Invalid - too little material
            
            # Normalize to 100%
            normalized = [a / total * 100 for a in amounts]
            
            # Build formulation
            formulation = self._build_formulation(opt_materials, normalized)
            
            # Check constraints
            constraint_penalty = self._check_constraints(formulation, constraints)
            if constraint_penalty > 0:
                return 1e6 + constraint_penalty
            
            # Predict properties
            result = self.predictor.predict_properties(formulation)
            
            if not result.get('success', False):
                return 1e6  # Prediction failed
            
            predictions = result.get('predictions', {})
            
            # Calculate objective (error from targets)
            error = self._calculate_objective_error(predictions, parsed_targets)
            
            return error
        
        # Run optimization
        opt_params = {**self.DEFAULT_OPT_PARAMS, **(optimization_params or {})}
        
        result = differential_evolution(
            objective,
            bounds,
            **opt_params
        )
        
        # Build final recipe
        final_amounts = result.x
        total = sum(final_amounts)
        normalized = [a / total * 100 for a in final_amounts]
        
        final_formulation = self._build_formulation(opt_materials, normalized)
        
        # Get final predictions
        pred_result = self.predictor.predict_properties(final_formulation)
        predictions = pred_result.get('predictions', {})
        
        # Calculate final score (1 = perfect match)
        final_error = result.fun if result.fun < 1e5 else 1.0
        optimization_score = max(0, 1 - final_error)
        
        return OptimizationResult(
            success=result.success and result.fun < 1e5,
            recipe=final_formulation.get('components', []),
            predicted_properties={k: round(v, 2) for k, v in predictions.items()},
            optimization_score=round(optimization_score, 3),
            iterations=iteration_count[0],
            message='Optimization successful' if result.success else result.message
        )
    
    def _parse_targets(self, targets: Dict) -> List[OptimizationTarget]:
        """Parse target dictionary into OptimizationTarget objects."""
        parsed = []
        
        for prop, value in targets.items():
            if isinstance(value, dict):
                target = OptimizationTarget(
                    property_name=prop,
                    target_value=float(value.get('value', value.get('target', 50))),
                    weight=float(value.get('weight', 1.0)),
                    direction=OptimizationDirection(value.get('direction', 'target')),
                    tolerance=float(value.get('tolerance', 0.05))
                )
            else:
                target = OptimizationTarget(
                    property_name=prop,
                    target_value=float(value),
                    weight=1.0,
                    direction=OptimizationDirection.TARGET
                )
            
            parsed.append(target)
        
        return parsed
    
    def _select_materials_for_optimization(self, constraints: Dict) -> List[Dict]:
        """Select materials to use in optimization based on constraints."""
        selected = []
        
        # Required categories
        required = constraints.get('required_categories', ['binder', 'pigment', 'solvent'])
        
        for category in required:
            if category in self.materials_by_category:
                # Take up to 3 materials per category
                selected.extend(self.materials_by_category[category][:3])
        
        # Add some additives
        if 'additive' in self.materials_by_category:
            selected.extend(self.materials_by_category['additive'][:2])
        
        # If no materials by category, use all available
        if not selected:
            selected = self.materials[:10]  # Limit to 10 for performance
        
        return selected
    
    def _build_formulation(self, materials: List[Dict], amounts: List[float]) -> Dict:
        """Build a formulation dictionary from materials and amounts."""
        components = []
        
        for mat, amount in zip(materials, amounts):
            if amount > 0.1:  # Skip very small amounts
                comp = {
                    'code': mat.get('code', mat.get('id', 'MAT')),
                    'name': mat.get('name', 'Unknown'),
                    'amount': round(amount, 2),
                    'category': mat.get('category', mat.get('material_category', 'other')),
                    'density': mat.get('density', 1.0),
                    'solid_content': mat.get('solid_content', 100),
                    'unit_price': mat.get('unit_price', 10),
                    'oil_absorption': mat.get('oil_absorption', 20),
                    'glass_transition': mat.get('glass_transition', 25),
                    'oh_value': mat.get('oh_value', 0),
                    'voc_g_l': mat.get('voc_g_l', 0),
                }
                components.append(comp)
        
        return {'components': components}
    
    def _check_constraints(self, formulation: Dict, constraints: Dict) -> float:
        """
        Check if formulation meets constraints.
        
        Returns:
            0 if all constraints met, positive penalty otherwise
        """
        penalty = 0
        components = formulation.get('components', [])
        
        if not components:
            return 1e6
        
        total_amount = sum(c.get('amount', 0) for c in components)
        
        # Max cost constraint
        if 'max_cost' in constraints:
            total_cost = sum(
                c.get('amount', 0) * c.get('unit_price', 10) / 100
                for c in components
            )
            if total_cost > constraints['max_cost']:
                penalty += (total_cost - constraints['max_cost']) * 10
        
        # Min solid content
        if 'min_solid_content' in constraints:
            solid = sum(
                c.get('amount', 0) * c.get('solid_content', 100) / 100
                for c in components
            )
            solid_pct = solid / total_amount * 100 if total_amount > 0 else 0
            
            if solid_pct < constraints['min_solid_content']:
                penalty += (constraints['min_solid_content'] - solid_pct) * 5
        
        # Max VOC
        if 'max_voc' in constraints:
            # Simplified VOC calculation
            voc_sum = sum(
                c.get('amount', 0) * c.get('voc_g_l', 0) / 1000
                for c in components
            )
            if voc_sum > constraints['max_voc'] / 1000:
                penalty += (voc_sum - constraints['max_voc'] / 1000) * 100
        
        return penalty
    
    def _calculate_objective_error(
        self,
        predictions: Dict[str, float],
        targets: List[OptimizationTarget]
    ) -> float:
        """Calculate weighted error between predictions and targets."""
        total_error = 0
        total_weight = sum(t.weight for t in targets)
        
        for target in targets:
            prop = target.property_name
            
            if prop not in predictions:
                total_error += target.weight  # Max penalty for missing prediction
                continue
            
            pred = predictions[prop]
            goal = target.target_value
            
            if goal == 0:
                goal = 0.01  # Avoid division by zero
            
            if target.direction == OptimizationDirection.MAXIMIZE:
                # Lower is worse
                if pred < goal:
                    error = (goal - pred) / goal
                else:
                    error = 0  # Met or exceeded
            
            elif target.direction == OptimizationDirection.MINIMIZE:
                # Higher is worse
                if pred > goal:
                    error = (pred - goal) / goal
                else:
                    error = 0  # Met or beat
            
            else:  # TARGET - match exactly
                error = abs(pred - goal) / abs(goal)
            
            # Apply tolerance
            if error < target.tolerance:
                error = 0
            
            total_error += target.weight * error
        
        # Normalize by total weight
        return total_error / total_weight if total_weight > 0 else total_error
    
    def quick_optimize(
        self,
        target_property: str,
        target_value: float,
        direction: str = 'target'
    ) -> OptimizationResult:
        """
        Quick single-target optimization.
        
        Args:
            target_property: Property name (e.g., 'gloss')
            target_value: Target value (e.g., 90)
            direction: 'max', 'min', or 'target'
            
        Returns:
            OptimizationResult
        """
        return self.optimize(
            targets={
                target_property: {
                    'value': target_value,
                    'direction': direction
                }
            },
            optimization_params={'maxiter': 50}  # Quick optimization
        )


# =============================================================================
# Convenience Functions
# =============================================================================

def optimize_recipe(
    predictor,
    materials: List[Dict],
    targets: Dict[str, float],
    constraints: Dict = None
) -> Dict:
    """
    Convenience function for recipe optimization.
    
    Args:
        predictor: ML predictor with predict_properties method
        materials: List of available materials
        targets: Target properties {'gloss': 90, 'viscosity': 2000}
        constraints: Optional constraints
        
    Returns:
        Result dictionary
    """
    optimizer = RecipeOptimizer(predictor, materials)
    result = optimizer.optimize(targets, constraints)
    
    return {
        'success': result.success,
        'recipe': result.recipe,
        'predicted': result.predicted_properties,
        'score': result.optimization_score,
        'iterations': result.iterations,
        'message': result.message
    }
