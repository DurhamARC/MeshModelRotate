function [Ttr]=Norm2Posing_for_GUI(vn,tra,SA)
%Position an artifact in preferred directions
%vn(i)=[xi yi zi]; unit normal vectors
%a=[x y z] is a unit vector in the preferred direction
%Strictly from our Paper:
%s(i) area of the triangle to which vn(i) is normal. Let A=S(s(i)) the
%surface area.
%Find a such that F=A^-1*S(s(i)*dot(a,vn(i))^2) -> max, under the constraint
%norm(a)=1 or G=dot(a,a)-1=0;
%using Lagrange multipliers: grad(F)=lambda*grad(G)
%after calculating partial derivative we have to solve the following matrix
%equation
%[Txx-lam     Txy           Tzx;...
% Txy         Tyy-lam       Tyz;...
% Tzx         Tyz           Tzz-lam] * [x; y; z]=0
Sxx=sum(tra.*(vn(:,1).^2));
Syy=sum(tra.*(vn(:,2).^2));
Szz=sum(tra.*(vn(:,3).^2));
Sxy=sum(tra.*(vn(:,1).*vn(:,2)));
Syz=sum(tra.*(vn(:,2).*vn(:,3)));
Szx=sum(tra.*(vn(:,3).*vn(:,1)));
%solution is easier by eigenvalues, eigenvectors
M=[Sxx Sxy Szx;...
    Sxy Syy Syz;...
    Szx Syz Szz];
M=M/SA;
[V,D]=eig(M);
[maxD,colmax]=max(max(D));%the column where to find max(D),usually col.3;
%according to the paper the corresponding vector is perpendicular to the
%major symmetry plane (x-axis?). Also the minimum eigenvalue corresponds to
%the eigenvector representing the z-axis
%the norm of each col in V is 1
[minD,colmin]=min(max(D));%values in D are always positive
%temporary positioning
zax=V(:,colmin);
xax=V(:,colmax);
tyax=cross(zax,xax);
csc=sort([colmin,colmax]);
if csc(1)==2, colav=1;
else % ==1
    if csc(2)==2, colav=3; else colav=2; end
end
if any(abs(V(:,colav)-tyax)>8*eps), %subtract the two vectors, if not all zeros
    yax=-V(:,colav);
    if any(abs(yax-tyax)>8*eps), % 8*eps is arbitrary
    %error('orthogonality problem - exiting');
    return
    end
else
    yax=V(:,colav);
end
%the transform
Ttr=[xax yax zax];


    