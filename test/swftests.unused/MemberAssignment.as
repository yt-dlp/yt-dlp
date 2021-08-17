// input: [1]
// output: 2

package {
public class MemberAssignment {
    public var v:int;

    public function g():int {
        return this.v;
    }

    public function f(a:int):int{
        this.v = a;
        return this.v + this.g();
    }

    public static function main(a:int): int {
        var v:MemberAssignment = new MemberAssignment();
        return v.f(a);
    }
}
}
