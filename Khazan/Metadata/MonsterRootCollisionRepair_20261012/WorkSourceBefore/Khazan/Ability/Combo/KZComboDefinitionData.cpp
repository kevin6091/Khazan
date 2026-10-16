


#include "Ability/Combo/KZComboDefinitionData.h"

const FKZComboNode* UKZComboDefinitionData::FindNode(const FName NodeId) const
{
	// 배열에서 같은 NodeId를 가진 첫 노드를 찾는다.
	return Nodes.FindByPredicate(
		[NodeId](const FKZComboNode& Node)
		{
			return Node.NodeId == NodeId;
		});
}
